"""Explicit SSH names across definition, CLI, state, and managed-file boundaries."""

from __future__ import annotations

import json
import shutil
import subprocess

import pytest
from typer.testing import CliRunner

from keywharf.cli import app
from keywharf.domain.errors import KeywharfError
from keywharf.domain.models import HostDefinition, LocalState, SelectedHostState, SSHHostConfig
from keywharf.services.apply import apply_selected_state
from keywharf.services.host_definitions import load_host_definition_map, resolve_selection
from keywharf.services.host_editor import update_host_definition
from keywharf.services.local_view import get_local_status, list_local_statuses
from keywharf.services.render import render_selected_state
from keywharf.services.selections import deselect_host, select_host
from keywharf.services.validate import validate_workspace
from keywharf.ssh_config.parser import parse_ssh_config
from keywharf.ssh_config.render import render_ssh_config
from keywharf.storage.state_store import load_state, save_state
from tests.support import load_config, make_workspace, read_json, write_json, write_manager_config

RUNNER = CliRunner()
SERVER = "demo-node-01"


@pytest.fixture
def workspace(tmp_path):
    root = make_workspace(tmp_path)
    write_manager_config(
        root / "config.json",
        host_repo_path="%{WORKSPACE}/repo",
        ssh_dir="%{WORKSPACE}/ssh",
        managed_config_path="%{WORKSPACE}/ssh/managed/config",
        managed_keys_dir="%{WORKSPACE}/ssh/managed/keys",
        state_path="%{WORKSPACE}/state/state.json",
    )
    config = load_config(root / "config.json", workspace_root=root)
    config.host_repo_path.mkdir()
    (config.host_repo_path / "keys").mkdir()
    (config.host_repo_path / "keys/demo_ed25519").write_text("SYNTHETIC TEST KEY\n")
    write_json(config.host_repo_path / "config.json", [definition()])
    return root, config


def definition():
    return {
        "ServerName": SERVER,
        "Aliases": ["work", "dev"],
        "Comment": "synthetic node",
        "Endpoint": [{"EndPointName": "direct", "HostName": "192.0.2.10", "Port": 22}],
        "Authentication": [
            {
                "AuthenticationName": "developer",
                "User": "developer",
                "IdentityFile": "keys/demo_ed25519",
            }
        ],
    }


def invoke(workspace, *args, input=None):
    return RUNNER.invoke(app, ["--workspace", str(workspace[0]), *args], input=input)


def select(config, names=None, **kwargs):
    return select_host(
        config, load_host_definition_map(config), server_name=SERVER, host_names=names, **kwargs
    )


def snapshot(root):
    return {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}


@pytest.mark.parametrize(
    "bad",
    [
        None,
        "dev",
        {},
        [1],
        [None],
        [""],
        ["dev", "DEV"],
        [SERVER],
        [SERVER.upper()],
        ["two names"],
        ["x\ny"],
        ["x\ty"],
        ["x\x00y"],
        ["*"],
        ["?"],
        ["!dev"],
        ["[ab]"],
        ["x#y"],
        ['x"y'],
        ["x'y"],
        ["a/b"],
        ["a\\b"],
        [".."],
        ["../dev"],
        ["-dev"],
        ["C:dev"],
        ["NUL"],
        ["dev."],
    ],
)
def test_alias_validation_is_strict(bad):
    with pytest.raises(ValueError):
        HostDefinition.from_dict({"ServerName": SERVER, "Aliases": bad})


@pytest.mark.parametrize("name", ["Demo_NODE-01.test", "_dev", "node-01", "node.test"])
def test_literal_names_preserve_spelling(name):
    host = HostDefinition.from_dict({"ServerName": name, "Aliases": ["Dev_01.test"]})
    assert host.to_dict()["ServerName"] == name
    assert host.aliases == ["Dev_01.test"]
    assert HostDefinition.from_dict({"ServerName": name}).aliases == []


@pytest.mark.parametrize("name", [None, 3, "", " foo", "foo ", "x\ny", "../x", "a/b", "a\\b", "*"])
def test_canonical_names_cannot_escape_key_paths(workspace, name):
    config = workspace[1]
    write_json(config.host_repo_path / "config.json", [{"ServerName": name}])
    before = snapshot(workspace[0])
    with pytest.raises(KeywharfError):
        render_selected_state(config)
    assert snapshot(workspace[0]) == before


@pytest.mark.parametrize(
    "other",
    [
        {"ServerName": SERVER},
        {"ServerName": SERVER.upper()},
        {"ServerName": "DEV"},
        {"ServerName": "other", "Aliases": [SERVER]},
        {"ServerName": "other", "Aliases": ["WORK"]},
    ],
)
def test_namespace_collisions_include_unselected_shells(workspace, other):
    config = workspace[1]
    write_json(config.host_repo_path / "config.json", [definition(), other])
    before = snapshot(workspace[0])
    assert not validate_workspace(config).ok
    for operation in (render_selected_state, apply_selected_state, load_host_definition_map):
        with pytest.raises(KeywharfError, match="Duplicate SSH name"):
            operation(config)
    assert snapshot(workspace[0]) == before


def test_selection_sets_defaults_order_and_preservation(workspace):
    config = workspace[1]
    select(config)
    assert load_state(config).get(SERVER).host_names == [SERVER]
    for names, expected in [
        (["dev"], ["dev"]),
        (["work", "dev", SERVER], [SERVER, "dev", "work"]),
        (["work"], ["work"]),
    ]:
        select(config, names)
        assert load_state(config).get(SERVER).host_names == expected
    first = select(config, ["work", SERVER, "dev"])[0].to_dict()
    second = select(config, ["dev", "work", SERVER])[0].to_dict()
    assert first == second
    select(config, ["dev"])
    payload = definition()
    payload["Aliases"].append("new-alias")
    payload["Endpoint"].append({"EndPointName": "alternate", "HostName": "192.0.2.11"})
    payload["Authentication"].append({"AuthenticationName": "alternate", "User": "tester"})
    write_json(
        config.host_repo_path / "config.json",
        [payload, {"ServerName": "draft", "Aliases": ["draft-alias"]}],
    )
    select(config, endpoint_name="alternate", authentication_name="alternate")
    entry = load_state(config).get(SERVER)
    assert entry.host_names == ["dev"]
    assert entry.endpoint_name == "alternate"
    assert entry.authentication_name == "alternate"
    assert render_selected_state(config).resolved_hosts[0].host_names == ["dev"]
    apply_selected_state(config)
    assert not validate_workspace(config).ok  # Unselected draft remains incomplete.


@pytest.mark.parametrize(
    "names", [[], ["missing"], ["DEV"], ["dev", "dev"], ["dev", "DEV"], ["a b"], [1]]
)
def test_failed_selection_is_atomic(workspace, names):
    config = workspace[1]
    select(config, ["work"])
    before = snapshot(workspace[0])
    with pytest.raises(KeywharfError):
        select(config, names)
    assert snapshot(workspace[0]) == before


def test_deleted_name_requires_explicit_replacement(workspace, monkeypatch):
    config = workspace[1]
    select(config, ["dev"])
    result = update_host_definition(config, server_name=SERVER, aliases=["work"])
    assert "--name" in result.warnings[0]
    before = snapshot(workspace[0])
    monkeypatch.setattr(
        "keywharf.commands._selection_prompt._supports_interactive_selection", lambda: True
    )
    failure = invoke(workspace, "select", SERVER, input="\n")
    assert failure.exit_code != 0
    assert "--name" in str(failure.exception)
    assert "Enter SSH" not in failure.output
    with pytest.raises(KeywharfError, match="--name"):
        apply_selected_state(config)
    assert snapshot(workspace[0]) == before
    assert invoke(workspace, "select", SERVER, "--name", "work").exit_code == 0
    assert load_state(config).get(SERVER).host_names == ["work"]


def test_cli_names_interactive_defaults_and_explicit_suppression(workspace, monkeypatch):
    config = workspace[1]
    assert invoke(workspace, "select", SERVER).exit_code == 0  # Non-TTY canonical default.
    assert load_state(config).get(SERVER).host_names == [SERVER]
    monkeypatch.setattr(
        "keywharf.commands._selection_prompt._supports_interactive_selection", lambda: True
    )
    result = invoke(workspace, "select", SERVER, input="\n")
    assert result.exit_code == 0
    assert "[1]" in result.output
    assert load_state(config).get(SERVER).host_names == [SERVER]
    result = invoke(workspace, "select", SERVER, input="0\n2,2\nx\n3,1\n")
    assert result.exit_code == 0, result.exception
    assert "Error:" in result.output
    assert load_state(config).get(SERVER).host_names == [SERVER, "dev"]
    result = invoke(workspace, "select", SERVER, input="\n")
    assert "[1,3]" in result.output
    assert load_state(config).get(SERVER).host_names == [SERVER, "dev"]
    result = invoke(workspace, "select", SERVER, "--name", "work")
    assert result.exit_code == 0
    assert "Enter SSH" not in result.output
    assert load_state(config).get(SERVER).host_names == ["work"]
    before = snapshot(workspace[0])
    result = invoke(workspace, "select", SERVER, "--name", "dev", "--name", "dev")
    assert result.exit_code != 0
    assert snapshot(workspace[0]) == before


@pytest.mark.parametrize("existing", [False, True])
@pytest.mark.parametrize("cancel", [False, True])
def test_name_prompt_eof_or_cancellation_never_writes(workspace, monkeypatch, existing, cancel):
    if existing:
        select(workspace[1], ["dev"])
    before = snapshot(workspace[0])
    monkeypatch.setattr(
        "keywharf.commands._selection_prompt._supports_interactive_selection", lambda: True
    )
    if cancel:

        def interrupt(*args, **kwargs):
            raise KeyboardInterrupt

        monkeypatch.setattr("keywharf.commands._selection_prompt.typer.prompt", interrupt)
    result = invoke(workspace, "select", SERVER, input="")
    assert result.exit_code != 0
    assert snapshot(workspace[0]) == before


def test_alias_crud_preserves_other_fields_and_order(workspace):
    config = workspace[1]
    payload = definition()
    payload["ExtraConfig"] = [
        {"Key": "ServerAliveInterval", "Value": "30", "Comment": "keep alive"}
    ]
    write_json(config.host_repo_path / "config.json", [payload])
    for args in [
        ("repo", "host", "add", "draft", "--alias", "scratch", "--alias", "Draft_2.test"),
        ("repo", "host", "update", SERVER, "--comment", "changed"),
        ("repo", "host", "endpoint", "update", SERVER, "direct", "--comment", "endpoint note"),
        ("repo", "host", "auth", "update", SERVER, "developer", "--comment", "auth note"),
    ]:
        result = invoke(workspace, *args)
        assert result.exit_code == 0, result.exception
    entries = read_json(config.host_repo_path / "config.json")
    assert [entry["ServerName"] for entry in entries] == [SERVER, "draft"]
    assert entries[0]["Aliases"] == ["work", "dev"]
    assert entries[0]["ExtraConfig"] == payload["ExtraConfig"]
    assert entries[0]["Authentication"][0]["IdentityFile"] == "keys/demo_ed25519"
    assert "Endpoint" not in entries[1] and "Authentication" not in entries[1]
    assert entries[1]["Aliases"] == ["scratch", "Draft_2.test"]
    assert (
        invoke(workspace, "repo", "host", "update", "draft", "--alias", "replacement").exit_code
        == 0
    )
    before = snapshot(workspace[0])
    for args in [
        ("--alias", "DEV"),
        ("--alias", "x", "--clear-aliases"),
        ("--alias", "x", "--alias", "x"),
    ]:
        assert invoke(workspace, "repo", "host", "update", "draft", *args).exit_code != 0
        assert snapshot(workspace[0]) == before
    assert invoke(workspace, "repo", "host", "update", "draft", "--clear-aliases").exit_code == 0
    assert load_host_definition_map(config)["draft"].aliases == []
    assert not config.state_path.exists()
    assert not config.managed_config_path.exists()


def test_canonical_rename_does_not_resolve_old_reference_through_alias(workspace):
    config = workspace[1]
    select(config, ["dev"])
    before = config.state_path.read_bytes()
    result = update_host_definition(
        config, server_name=SERVER, new_name="renamed-node", aliases=[SERVER, "dev"]
    )
    assert result.warnings
    assert config.state_path.read_bytes() == before
    assert get_local_status(config, SERVER).status == "invalid"
    with pytest.raises(KeywharfError, match="not present"):
        render_selected_state(config)
    select_host(
        config, load_host_definition_map(config), server_name="renamed-node", host_names=[SERVER]
    )
    assert load_state(config).get(SERVER) is not None


@pytest.mark.parametrize("version", [1, None])
def test_v1_boundary_preserves_choices_and_read_only_bytes(workspace, version):
    config = workspace[1]
    other = definition()
    other.update(ServerName="other-node", Aliases=[])
    write_json(config.host_repo_path / "config.json", [definition(), other])
    payload = {
        "selected_hosts": [
            {"server_name": SERVER, "endpoint_name": "direct", "authentication_name": "developer"},
            {"server_name": "other-node", "endpoint_name": None, "authentication_name": None},
        ]
    }
    if version is not None:
        payload["version"] = version
    write_json(config.state_path, payload)
    before = snapshot(workspace[0])
    converted = load_state(config)
    assert converted.version == 2
    assert converted.get(SERVER).host_names == [SERVER]
    assert converted.get("other-node").endpoint_name is None
    assert converted.get("other-node").authentication_name is None
    for args in [
        ("render", "--json"),
        ("validate", "--json"),
        ("show", "local", SERVER, "--json"),
        ("list", "repo", "--json"),
        ("apply", "--dry-run"),
    ]:
        result = invoke(workspace, *args)
        assert result.exit_code == 0, result.exception
    assert snapshot(workspace[0]) == before
    apply_selected_state(config)
    assert read_json(config.state_path) == payload  # Apply doesn't migrate state.
    assert not list(config.state_path.parent.glob("*.bak*"))
    assert invoke(workspace, "select", SERVER, "--name", "dev").exit_code == 0
    saved = read_json(config.state_path)
    assert saved["version"] == 2
    assert saved["selected_hosts"][0]["host_names"] == ["dev"]
    retained = saved["selected_hosts"][1]
    assert retained == {**payload["selected_hosts"][1], "host_names": ["other-node"]}


@pytest.mark.parametrize(
    "payload",
    [
        {"version": 2, "selected_hosts": [{"server_name": SERVER}]},
        *[
            {"version": 2, "selected_hosts": [{"server_name": SERVER, "host_names": value}]}
            for value in [None, [], "dev", [1], ["dev", "dev"]]
        ],
        {"version": 1, "selected_hosts": [{"server_name": SERVER, "host_names": [SERVER]}]},
        {"selected_hosts": [{"server_name": SERVER, "host_names": [SERVER]}]},
        *[{"version": version, "selected_hosts": []} for version in [3, 99, None, "2", 2.0, True]],
    ],
)
def test_invalid_state_is_not_guessed_or_rewritten(workspace, payload):
    config = workspace[1]
    write_json(config.state_path, payload)
    before = snapshot(workspace[0])
    with pytest.raises(KeywharfError):
        load_state(config)
    assert invoke(workspace, "select", SERVER, "--name", "dev").exit_code != 0
    assert snapshot(workspace[0]) == before


def test_state_replace_failure_keeps_previous_bytes(workspace, monkeypatch):
    config = workspace[1]
    select(config, ["dev"])
    before = config.state_path.read_bytes()

    def fail(*args):
        raise OSError("replacement failed")

    monkeypatch.setattr("keywharf.storage.state_store.os.replace", fail)
    with pytest.raises(OSError):
        select(config, ["work"])
    assert config.state_path.read_bytes() == before
    assert not config.state_path.with_name("state.json.tmp").exists()


def test_managed_roundtrip_legacy_new_and_windows_paths():
    legacy = (
        "# This file is managed by keywharf\r\n# human\r\nHost Demo_NODE.test\r\n"
        "\tHostName 192.0.2.10\r\n\tIdentityFile C:\\ssh\\keys\\test\r\n"
    )
    host = parse_ssh_config(legacy)[0]
    assert host.server_name == "Demo_NODE.test"
    assert host.host_names == ["Demo_NODE.test"]
    assert host.authentication.identity_file == "C:/ssh/keys/test"
    host.host_names = ["work", "dev"]
    rendered = render_ssh_config([host])
    assert "# human\n# keywharf-owner: Demo_NODE.test\nHost dev work" in rendered
    assert parse_ssh_config(rendered)[0].to_dict() == host.to_dict()
    assert parse_ssh_config(rendered.replace("\n", "\r\n"))[0].to_dict() == host.to_dict()


@pytest.mark.parametrize(
    "content",
    [
        "#keywharf-owner: node\nHost dev\n",
        "# KEYWHARF-OWNER: node\nHost dev\n",
        "Host dev work\n",
        "Host dev\nHost DEV\n",
        "# keywharf-owner: node\n# keywharf-owner: node\nHost dev\n",
        "# keywharf-owner: node\nHost dev\n# keywharf-owner: NODE\nHost work\n",
        "# keywharf-owner: node\nHost dev\n# keywharf-owner: other\nHost dev\n",
        "# keywharf-owner: node\nHost dev\nHost node\n",
        "# keywharf-owner: ../node\nHost dev\n",
        "# keywharf-owner: node\n",
        "# keywharf-owner node\nHost dev\n",
        "Host dev\n# keywharf-owner: node\nUser test\n",
        "# keywharf-owner: node\nHost dev DEV\n",
    ],
)
def test_ambiguous_or_malformed_managed_ownership_is_rejected(content):
    with pytest.raises(ValueError):
        parse_ssh_config(content)


def test_managed_identity_disjoint_names_orphans_and_key_lifecycle(workspace):
    config = workspace[1]
    select(config, [SERVER, "dev"])
    plan = render_selected_state(config)
    assert len(plan.planned_key_copies) == 1
    apply_selected_state(config)
    key = config.managed_keys_dir / SERVER / "demo_ed25519"
    original = key.stat().st_mtime_ns
    for names in [["dev"], ["work"]]:
        select(config, names)
        status = get_local_status(config, SERVER)
        assert status.status == "pending"
        assert status.current_host.server_name == SERVER
        plan = render_selected_state(config)
        assert not plan.orphaned_hosts
        assert not plan.planned_key_copies and not plan.planned_key_deletes
        apply_selected_state(config)
        assert get_local_status(config, SERVER).status == "applied"
        assert key.stat().st_mtime_ns == original
        assert len(list(config.managed_keys_dir.rglob("demo_ed25519"))) == 1
    (config.host_repo_path / "config.json").unlink()
    assert get_local_status(config, SERVER).status == "invalid"
    write_json(config.host_repo_path / "config.json", [definition()])
    deselect_host(config, server_name=SERVER)
    assert [(s.server_name, s.status) for s in list_local_statuses(config)] == [
        (SERVER, "orphaned")
    ]
    with pytest.raises(KeywharfError, match="--allow-empty"):
        apply_selected_state(config)
    assert key.exists()
    apply_selected_state(config, allow_empty=True)
    assert not key.exists()
    assert not list_local_statuses(config)


def test_config_replacement_failure_cannot_delete_old_key(workspace, monkeypatch):
    config = workspace[1]
    select(config, ["dev"])
    apply_selected_state(config)
    before = config.managed_config_path.read_bytes()
    old_key = config.managed_keys_dir / SERVER / "demo_ed25519"
    payload = definition()
    payload["Authentication"][0]["IdentityFile"] = "keys/replacement"
    (config.host_repo_path / "keys/replacement").write_text("NEW SYNTHETIC KEY")
    write_json(config.host_repo_path / "config.json", [payload])

    def fail_replace(*args):
        assert (config.managed_keys_dir / SERVER / "replacement").exists()
        raise OSError("managed config replacement failed")

    monkeypatch.setattr("keywharf.storage.ssh_files.os.replace", fail_replace)
    with pytest.raises(OSError):
        apply_selected_state(config)
    assert old_key.exists()
    assert config.managed_config_path.read_bytes() == before


def test_direct_models_and_services_cannot_bypass_name_validation(workspace):
    host = HostDefinition.from_dict(definition())
    host.aliases = ["dev", "DEV"]
    selection = SelectedHostState(SERVER, ["dev"])
    with pytest.raises(KeywharfError):
        resolve_selection({SERVER: host}, selection)
    with pytest.raises(ValueError):
        render_ssh_config([SSHHostConfig(SERVER, ["*"])])
    state = LocalState(selected_hosts=[selection, selection])
    with pytest.raises(KeywharfError, match="duplicate"):
        save_state(workspace[1], state)
    assert not workspace[1].state_path.exists()


def test_cli_complete_disposable_flow_and_views(workspace):
    config = workspace[1]
    write_json(config.host_repo_path / "config.json", [])
    for args in [
        ("repo", "host", "add", SERVER, "--alias", "dev", "--alias", "work"),
        (
            "repo",
            "host",
            "endpoint",
            "add",
            SERVER,
            "direct",
            "--hostname",
            "192.0.2.10",
            "--port",
            "22",
        ),
        (
            "repo",
            "host",
            "auth",
            "add",
            SERVER,
            "developer",
            "--user",
            "developer",
            "--identity-file",
            "keys/demo_ed25519",
        ),
        ("select", SERVER, "--name", "dev", "--name", SERVER),
        ("render", "--json"),
        ("apply",),
    ]:
        result = invoke(workspace, *args)
        assert result.exit_code == 0, (args, result.exception, result.output)
    for names in [["dev"], ["work"]]:
        assert invoke(workspace, "select", SERVER, "--name", names[0]).exit_code == 0
        assert invoke(workspace, "apply").exit_code == 0
        for canonical, facade in [
            (("local", "show", SERVER), ("show", "local", SERVER)),
            (("local", "list"), ("list", "local")),
            (("repo", "host", "show", SERVER), ("show", "repo", SERVER)),
            (("repo", "host", "list"), ("list", "repo")),
        ]:
            for flags in [(), ("--json",)]:
                first = invoke(workspace, *canonical, *flags)
                second = invoke(workspace, *facade, *flags)
                assert first.exit_code == second.exit_code == 0
                assert first.output == second.output
        result = json.loads(invoke(workspace, "show", "local", SERVER, "--json").output)
        assert result["status"] == "applied"
        assert result["current_host"]["server_name"] == SERVER
        assert result["current_host"]["host_names"] == names
        assert "name" not in result["current_host"]
    assert invoke(workspace, "deselect", SERVER).exit_code == 0
    assert invoke(workspace, "apply", "--allow-empty").exit_code == 0
    assert not config.main_config_path.exists()


@pytest.mark.parametrize(
    "args, flag",
    [
        (("select",), "--name"),
        (("repo", "host", "add"), "--alias"),
        (("repo", "host", "update"), "--clear-aliases"),
    ],
)
def test_new_options_are_documented_in_help(args, flag):
    result = RUNNER.invoke(app, [*args, "--help"], env={"COLUMNS": "160", "TERM": "dumb"})
    assert result.exit_code == 0
    assert flag in result.output


def test_openssh_resolves_both_names_without_network(workspace):
    ssh = shutil.which("ssh")
    if ssh is None:
        pytest.skip("OpenSSH ssh executable unavailable")
    config = workspace[1]
    select(config, ["dev", SERVER])
    apply_selected_state(config)
    effective = []
    for name in [SERVER, "dev"]:
        result = subprocess.run(
            [ssh, "-G", "-F", str(config.managed_config_path), name],
            capture_output=True,
            text=True,
            check=True,
        )
        fields = dict(line.split(None, 1) for line in result.stdout.splitlines() if " " in line)
        effective.append({key: fields[key] for key in ["hostname", "port", "user", "identityfile"]})
    assert (
        effective[0]
        == effective[1]
        == {
            "hostname": "192.0.2.10",
            "port": "22",
            "user": "developer",
            "identityfile": (config.managed_keys_dir / SERVER / "demo_ed25519").as_posix(),
        }
    )


@pytest.mark.parametrize(
    "args, module, expected",
    [
        (
            ("select", SERVER, "--name", "dev", "--name", SERVER, "--sudo"),
            "keywharf.commands.select",
            ["--name", "dev", "--name", SERVER],
        ),
        (
            ("repo", "host", "add", "draft", "--alias", "scratch", "--alias", "work-2", "--sudo"),
            "keywharf.commands.repo.helpers",
            ["--alias", "scratch", "--alias", "work-2"],
        ),
        (
            ("repo", "host", "update", SERVER, "--alias", "scratch", "--alias", "work-2", "--sudo"),
            "keywharf.commands.repo.helpers",
            ["--alias", "scratch", "--alias", "work-2"],
        ),
    ],
)
def test_actual_typer_repeated_options_survive_sudo_reconstruction(
    workspace, monkeypatch, args, module, expected
):
    captured = []

    def fake_reexec(**kwargs):
        assert kwargs["sudo_requested"]
        captured.extend(kwargs["invocation"].with_sudo_flag().argv)
        return True

    monkeypatch.setattr(f"{module}.maybe_reexec_with_sudo", fake_reexec)
    before = snapshot(workspace[0])
    result = invoke(workspace, *args)
    assert result.exit_code == 0, result.exception
    position = captured.index(expected[0])
    assert captured[position : position + len(expected)] == expected
    assert captured[-1] == "--sudo"
    assert captured[:2] == ["--workspace", str(workspace[0])]
    assert snapshot(workspace[0]) == before


def test_first_interactive_selection_default_and_single_name_suppression(workspace, monkeypatch):
    monkeypatch.setattr(
        "keywharf.commands._selection_prompt._supports_interactive_selection", lambda: True
    )
    assert invoke(workspace, "select", SERVER, input="\n").exit_code == 0
    assert load_state(workspace[1]).get(SERVER).host_names == [SERVER]
    update_host_definition(workspace[1], server_name=SERVER, clear_aliases=True)
    result = invoke(workspace, "select", SERVER)
    assert result.exit_code == 0
    assert "Enter SSH" not in result.output


def test_missing_state_read_only_commands_do_not_create_it(workspace):
    before = snapshot(workspace[0])
    for args in [("render", "--json"), ("local", "list", "--json"), ("validate", "--json")]:
        assert invoke(workspace, *args).exit_code == 0
    assert snapshot(workspace[0]) == before


def test_v1_deselect_writes_v2_for_all_retained_entries(workspace):
    config = workspace[1]
    write_json(
        config.state_path,
        {
            "version": 1,
            "selected_hosts": [
                {
                    "server_name": SERVER,
                    "endpoint_name": "direct",
                    "authentication_name": "developer",
                },
                {"server_name": "other-node", "endpoint_name": None, "authentication_name": None},
            ],
        },
    )
    assert invoke(workspace, "deselect", SERVER).exit_code == 0
    assert read_json(config.state_path) == {
        "version": 2,
        "selected_hosts": [
            {
                "server_name": "other-node",
                "host_names": ["other-node"],
                "endpoint_name": None,
                "authentication_name": None,
            },
        ],
    }


def test_endpoint_and_auth_add_remove_preserve_aliases(workspace):
    for args in [
        ("repo", "host", "endpoint", "add", SERVER, "alternate", "--hostname", "192.0.2.11"),
        ("repo", "host", "auth", "add", SERVER, "alternate", "--user", "tester"),
        ("repo", "host", "endpoint", "remove", SERVER, "alternate"),
        ("repo", "host", "auth", "remove", SERVER, "alternate"),
    ]:
        result = invoke(workspace, *args)
        assert result.exit_code == 0, result.exception
        assert read_json(workspace[1].host_repo_path / "config.json")[0]["Aliases"] == [
            "work",
            "dev",
        ]


def test_alias_add_collision_and_removed_host_warning_without_state_changes(workspace):
    config = workspace[1]
    before = snapshot(workspace[0])
    for args in [
        ("repo", "host", "add", "DEV"),
        ("repo", "host", "add", "another", "--alias", "WORK"),
    ]:
        assert invoke(workspace, *args).exit_code != 0
        assert snapshot(workspace[0]) == before
    select(config, ["dev"])
    state = config.state_path.read_bytes()
    result = invoke(workspace, "repo", "host", "remove", SERVER, "--json")
    assert result.exit_code == 0, result.exception
    assert json.loads(result.output)["warnings"]
    assert config.state_path.read_bytes() == state
    assert get_local_status(config, SERVER).status == "invalid"


def test_endpoint_prompt_eof_after_name_selection_leaves_state_unchanged(workspace, monkeypatch):
    config = workspace[1]
    select(config, ["dev"])
    payload = definition()
    payload["Endpoint"].append({"EndPointName": "alternate", "HostName": "192.0.2.11"})
    write_json(config.host_repo_path / "config.json", [payload])
    monkeypatch.setattr(
        "keywharf.commands._selection_prompt._supports_interactive_selection", lambda: True
    )
    before = snapshot(workspace[0])
    result = invoke(workspace, "select", SERVER, input="2\n")
    assert result.exit_code != 0
    assert snapshot(workspace[0]) == before


def test_ambiguous_existing_managed_config_blocks_apply_before_any_writes(workspace):
    config = workspace[1]
    select(config, ["dev"])
    config.managed_config_path.parent.mkdir(parents=True)
    config.managed_config_path.write_text("# keywharf-owner: demo-node-01\nHost dev\nHost dev\n")
    before = snapshot(workspace[0])
    with pytest.raises(KeywharfError, match="Invalid managed config"):
        apply_selected_state(config)
    assert snapshot(workspace[0]) == before
    assert not validate_workspace(config).ok


def test_reserved_ownership_comment_cannot_be_forged_by_human_comment(workspace):
    config = workspace[1]
    select(config, ["dev"])
    payload = definition()
    payload["Comment"] = "keywharf-owner: other-node"
    write_json(config.host_repo_path / "config.json", [payload])
    before = snapshot(workspace[0])
    with pytest.raises(KeywharfError, match="reserved"):
        apply_selected_state(config)
    assert snapshot(workspace[0]) == before
