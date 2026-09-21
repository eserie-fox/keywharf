"""Human comment fidelity, structural validation, repair, and no-op materialization."""

from __future__ import annotations

import json
from unittest.mock import Mock

import pytest
from typer.testing import CliRunner

from keywharf.cli import app
from keywharf.domain.errors import KeywharfError
from keywharf.domain.models import (
    HostDefinition,
    SSHAuthentication,
    SSHEndpoint,
    SSHExtraConfig,
    SSHHostConfig,
)
from keywharf.services.apply import apply_selected_state
from keywharf.services.host_definitions import load_host_definition_list, load_host_definition_map
from keywharf.services.host_repo_editor_common import persist_host_definitions
from keywharf.services.local_view import get_local_status
from keywharf.services.render import render_selected_state
from keywharf.services.selections import select_host
from keywharf.services.validate import validate_workspace
from keywharf.ssh_config.parser import parse_ssh_config
from keywharf.ssh_config.render import render_ssh_config
from keywharf.storage.ssh_files import MANAGED_SSH_HEADER
from tests.support import load_config, make_workspace, read_json, write_json, write_manager_config

SERVER = "demo-node-01"
LOCATIONS = ["host", "endpoint", "authentication", "extra"]
RUNNER = CliRunner()


def ssh_host():
    return SSHHostConfig(
        server_name=SERVER,
        host_names=["dev"],
        endpoint=SSHEndpoint(hostname="192.0.2.10", port=22),
        authentication=SSHAuthentication(user="developer", identity_file="/tmp/test-key"),
        extra_config=[SSHExtraConfig(key="ServerAliveInterval", value="30")],
    )


def comment_object(host, location):
    return {
        "host": host,
        "endpoint": host.endpoint,
        "authentication": host.authentication,
        "extra": host.extra_config[0],
    }[location]


def comment_payload(host, location):
    return {
        "host": host,
        "endpoint": host["Endpoint"][0],
        "authentication": host["Authentication"][0],
        "extra": host["ExtraConfig"][0],
    }[location]


def definition():
    return {
        "ServerName": SERVER,
        "Aliases": ["dev", "work"],
        "Endpoint": [{"EndPointName": "direct", "HostName": "192.0.2.10", "Port": 22}],
        "Authentication": [
            {
                "AuthenticationName": "developer",
                "User": "developer",
                "IdentityFile": "keys/demo_ed25519",
            }
        ],
        "ExtraConfig": [{"Key": "ServerAliveInterval", "Value": "30"}],
    }


@pytest.fixture
def workspace(tmp_path):
    root = make_workspace(tmp_path)
    write_manager_config(
        root / "config.json",
        host_repo_path="%{WORKSPACE}/repo",
        ssh_dir="%{WORKSPACE}/ssh",
        state_path="%{WORKSPACE}/state/state.json",
        managed_config_path="%{WORKSPACE}/ssh/managed/config",
        managed_keys_dir="%{WORKSPACE}/ssh/managed/keys",
    )
    config = load_config(root / "config.json", workspace_root=root)
    write_json(config.host_repo_path / "config.json", [definition()])
    key = config.host_repo_path / "keys/demo_ed25519"
    key.parent.mkdir()
    key.write_text("SYNTHETIC KEY\n", encoding="utf-8")
    select_host(
        config,
        load_host_definition_map(config),
        server_name=SERVER,
        host_names=["dev"],
        endpoint_name="direct",
        authentication_name="developer",
    )
    return config


def invoke(config, *args):
    return RUNNER.invoke(app, ["--workspace", str(config.workspace_root), *args])


def snapshot(config):
    return {
        p.relative_to(config.workspace_root): p.read_bytes()
        for p in config.workspace_root.rglob("*")
        if p.is_file()
    }


@pytest.mark.parametrize("location", LOCATIONS)
@pytest.mark.parametrize(
    "comment",
    [
        None,
        "",
        "single line",
        "first line\nsecond line",
        "first line\n\nsecond line",
        "first line\n  indented  \n \nsecond line",
        "你好 café 🔑\n第二行",
        "This file is managed by keywharf",
        "first\nThis file is managed by keywharf\nlast",
        "mentions keywharf-owner in the middle",
    ],
)
@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_comment_roundtrip(location, comment, newline):
    host = ssh_host()
    comment_object(host, location).comment = (
        comment.replace("\n", newline) if comment is not None else None
    )
    rendered = render_ssh_config([host])
    parsed = parse_ssh_config(rendered.replace("\n", newline))[0]
    expected = comment or None
    assert comment_object(parsed, location).comment == expected
    assert parsed.to_dict() == host.to_dict()


def test_combined_comments_do_not_leak_between_fields_or_hosts():
    hosts = [ssh_host(), ssh_host()]
    hosts[1].server_name = "other-node"
    hosts[1].host_names = ["work"]
    for index, host in enumerate(hosts):
        for location in LOCATIONS:
            comment_object(host, location).comment = f"{index} {location}\n\n独立した行"
    assert [h.to_dict() for h in parse_ssh_config(render_ssh_config(hosts))] == [
        h.to_dict() for h in hosts
    ]


@pytest.mark.parametrize("location", LOCATIONS)
def test_loaded_and_direct_comments_normalize_outer_whitespace_and_crlf(location):
    raw = " \r\n first line\r\n\r\n  second line  \r\n "
    expected = "first line\n\n  second line"
    payload = definition()
    comment_payload(payload, location)["Comment"] = raw
    loaded = HostDefinition.from_dict(payload).to_dict()
    assert comment_payload(loaded, location)["Comment"] == expected
    direct = {
        "host": SSHHostConfig(SERVER, ["dev"], comment=raw),
        "endpoint": SSHEndpoint(comment=raw),
        "authentication": SSHAuthentication(comment=raw),
        "extra": SSHExtraConfig(comment=raw),
    }[location]
    assert direct.comment == expected
    assert direct.to_dict()["comment"] == expected


@pytest.mark.parametrize("kind", [SSHEndpoint, SSHAuthentication])
def test_comment_accumulation_keeps_line_boundaries(kind):
    item = kind(comment="first\r\n\r\nsecond")
    item.add_comment("third\r\nfourth")
    item.add_comment("")
    assert item.comment == "first\n\nsecond\nthird\nfourth"


@pytest.mark.parametrize("location", LOCATIONS)
def test_multiline_comments_stay_in_sync_and_real_edits_are_materialized(workspace, location):
    config = workspace
    payload = definition()
    for field in LOCATIONS:
        comment_payload(payload, field)["Comment"] = f"{field} first\r\n\r\n{field} café"
    write_json(config.host_repo_path / "config.json", [payload])
    before = snapshot(config)
    assert validate_workspace(config).ok
    render_selected_state(config)
    assert snapshot(config) == before
    assert apply_selected_state(config).changed
    result = invoke(config, "local", "show", SERVER, "--json")
    assert result.exit_code == 0, result.output
    status = json.loads(result.output)
    assert status["status"] == "applied"
    assert render_selected_state(config).in_sync
    for field in LOCATIONS:
        current = get_local_status(config, SERVER).current_host
        assert comment_object(current, field).comment == f"{field} first\n\n{field} café"
    state_before = config.state_path.read_bytes()
    comment_payload(payload, location)["Comment"] += "\r\nreal edit"
    write_json(config.host_repo_path / "config.json", [payload])
    assert get_local_status(config, SERVER).status == "pending"
    assert not render_selected_state(config).in_sync
    assert apply_selected_state(config).changed
    assert get_local_status(config, SERVER).status == "applied"
    assert render_selected_state(config).in_sync
    assert config.state_path.read_bytes() == state_before
    assert comment_object(get_local_status(config, SERVER).current_host, location).comment == (
        f"{location} first\n\n{location} café\nreal edit"
    )


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_second_apply_does_not_replace_backup_or_touch_keys(workspace, monkeypatch, newline):
    config = workspace
    apply_selected_state(config)
    config.managed_config_path.write_bytes(
        config.managed_config_path.read_text(encoding="utf-8").replace("\n", newline).encode()
    )
    before = snapshot(config)
    writes = Mock()
    copies = Mock()
    deletes = Mock()
    monkeypatch.setattr("keywharf.services.managed_config_applier.write_managed_config", writes)
    monkeypatch.setattr("keywharf.services.apply.copy_identity_file", copies)
    monkeypatch.setattr("keywharf.services.apply.delete_identity_file", deletes)
    result = apply_selected_state(config)
    assert not result.changed
    writes.assert_not_called()
    copies.assert_not_called()
    deletes.assert_not_called()
    assert snapshot(config) == before


def test_legacy_fragment_rewrite_is_reported_even_when_semantically_in_sync(workspace):
    config = workspace
    select_host(config, load_host_definition_map(config), server_name=SERVER, host_names=[SERVER])
    apply_selected_state(config)
    original = config.managed_config_path.read_text(encoding="utf-8")
    legacy = original.replace(f"# keywharf-owner: {SERVER}\n", "")
    config.managed_config_path.write_text(legacy, encoding="utf-8")
    assert render_selected_state(config).in_sync
    before = snapshot(config)
    assert apply_selected_state(config, dry_run=True).changed
    assert snapshot(config) == before
    assert apply_selected_state(config).changed
    assert config.managed_config_path.read_text(encoding="utf-8") == original
    assert not apply_selected_state(config).changed


FORBIDDEN = ["keywharf-owner: other-node", "first\n\t KeYwHaRf-OwNeR: other-node"]


@pytest.mark.parametrize("location", LOCATIONS)
@pytest.mark.parametrize("comment", FORBIDDEN)
def test_reserved_comments_fail_workspace_validation_with_context(workspace, location, comment):
    config = workspace
    payload = definition()
    comment_payload(payload, location)["Comment"] = comment
    write_json(config.host_repo_path / "config.json", [payload])
    before = snapshot(config)
    result = invoke(config, "validate", "--json")
    assert result.exit_code == 1
    errors = json.loads(result.output)["errors"]
    context = {
        "host": "Comment",
        "endpoint": "direct",
        "authentication": "developer",
        "extra": "ServerAliveInterval",
    }[location]
    assert any(SERVER in e and context in e and "reserved" in e for e in errors)
    with pytest.raises(KeywharfError, match="reserved"):
        persist_host_definitions(config, load_host_definition_list(config))
    assert snapshot(config) == before


@pytest.mark.parametrize("location", LOCATIONS)
@pytest.mark.parametrize("comment", FORBIDDEN)
def test_direct_renderer_rejects_reserved_comments(location, comment):
    host = ssh_host()
    comment_object(host, location).comment = comment
    with pytest.raises(ValueError, match="reserved"):
        render_ssh_config([host])


CRUD = [
    ("host", ("repo", "host", "update", SERVER)),
    ("endpoint", ("repo", "host", "endpoint", "update", SERVER, "direct")),
    ("authentication", ("repo", "host", "auth", "update", SERVER, "developer")),
]


@pytest.mark.parametrize("location,command", CRUD)
@pytest.mark.parametrize("comment", FORBIDDEN)
def test_forbidden_crud_updates_preserve_every_file(workspace, location, command, comment):
    config = workspace
    apply_selected_state(config)
    before = snapshot(config)
    result = invoke(config, *command, "--comment", comment)
    assert result.exit_code == 1
    assert isinstance(result.exception, KeywharfError)
    assert "reserved" in str(result.exception)
    assert snapshot(config) == before


@pytest.mark.parametrize("location,command", CRUD)
@pytest.mark.parametrize("clear", [False, True])
def test_invalid_comments_can_be_explicitly_repaired(workspace, location, command, clear):
    config = workspace
    payload = definition()
    comment_payload(payload, location)["Comment"] = FORBIDDEN[1]
    write_json(config.host_repo_path / "config.json", [payload])
    state = config.state_path.read_bytes()
    args = ("--clear-comment",) if clear else ("--comment", "repaired\n\ncomment")
    result = invoke(config, *command, *args)
    assert result.exit_code == 0, result.exception
    saved = read_json(config.host_repo_path / "config.json")[0]
    assert comment_payload(saved, location).get("Comment") == (
        None if clear else "repaired\n\ncomment"
    )
    assert validate_workspace(config).ok
    assert config.state_path.read_bytes() == state
    assert not config.managed_config_path.exists()


def test_invalid_shell_add_is_rejected_and_unselected_comments_are_structural(workspace):
    config = workspace
    before = snapshot(config)
    result = invoke(config, "repo", "host", "add", "draft", "--comment", FORBIDDEN[1])
    assert result.exit_code == 1
    assert snapshot(config) == before
    write_json(
        config.host_repo_path / "config.json",
        [
            definition(),
            {
                "ServerName": "draft",
                "Comment": FORBIDDEN[1],
            },
        ],
    )
    assert any("draft" in e and "reserved" in e for e in validate_workspace(config).errors)
    with pytest.raises(KeywharfError, match="reserved"):
        render_selected_state(config)
    assert invoke(config, "repo", "host", "update", "draft", "--clear-comment").exit_code == 0
    assert render_selected_state(config).resolved_hosts[0].host_names == ["dev"]
    validation = validate_workspace(config)
    assert not validation.ok  # The unselected shell is still incomplete.
    assert not any("reserved" in e for e in validation.errors)


@pytest.mark.parametrize("field", ["Endpoint", "Authentication"])
def test_reserved_comments_on_unused_options_are_structural(workspace, field):
    payload = definition()
    unused = dict(payload[field][0])
    name_key = "EndPointName" if field == "Endpoint" else "AuthenticationName"
    unused.update({name_key: "unused", "Comment": FORBIDDEN[1]})
    payload[field].append(unused)
    write_json(workspace.host_repo_path / "config.json", [payload])
    errors = validate_workspace(workspace).errors
    assert any("unused" in e and field in e and "reserved" in e for e in errors)


def test_header_is_only_consumed_at_file_header_position():
    host = parse_ssh_config(
        f"{MANAGED_SSH_HEADER}\n\n# human\n{MANAGED_SSH_HEADER}\n"
        f"# keywharf-owner: {SERVER}\nHost dev\n"
        f"    {MANAGED_SSH_HEADER}\n    HostName 192.0.2.10\n"
    )[0]
    assert host.comment == "human\nThis file is managed by keywharf"
    assert host.endpoint.comment == "This file is managed by keywharf"


def test_key_work_is_reported_without_rewriting_identical_fragment(workspace, monkeypatch):
    from keywharf.services.managed_config_applier import validate_managed_config

    config = workspace
    apply_selected_state(config)
    original = config.managed_config_path.read_bytes()
    source = config.host_repo_path / "keys/demo_ed25519"
    source.write_text("UPDATED SYNTHETIC KEY\n", encoding="utf-8")
    stale = config.managed_keys_dir / "old-node/stale"
    stale.parent.mkdir()
    stale.write_text("STALE SYNTHETIC KEY\n", encoding="utf-8")
    writes = Mock()
    validation = Mock(wraps=validate_managed_config)
    monkeypatch.setattr("keywharf.services.managed_config_applier.write_managed_config", writes)
    monkeypatch.setattr(
        "keywharf.services.managed_config_applier.validate_managed_config", validation
    )
    result = apply_selected_state(config)
    assert result.changed
    assert result.copied_keys == [config.managed_keys_dir / SERVER / "demo_ed25519"]
    assert result.deleted_keys == [stale]
    assert result.copied_keys[0].read_bytes() == source.read_bytes()
    assert not stale.exists()
    validation.assert_called_once()
    writes.assert_not_called()
    assert config.managed_config_path.read_bytes() == original


def test_identical_fragment_still_validates_before_stale_cleanup(workspace, monkeypatch):
    config = workspace
    apply_selected_state(config)
    stale = config.managed_keys_dir / "old-node/stale"
    stale.parent.mkdir()
    stale.write_text("STALE SYNTHETIC KEY\n", encoding="utf-8")
    before = snapshot(config)
    validation = Mock(side_effect=KeywharfError("synthetic validation failure"))
    deletes = Mock()
    monkeypatch.setattr(
        "keywharf.services.managed_config_applier.validate_managed_config", validation
    )
    monkeypatch.setattr("keywharf.services.apply.delete_identity_file", deletes)
    with pytest.raises(KeywharfError, match="synthetic validation failure"):
        apply_selected_state(config)
    validation.assert_called_once()
    deletes.assert_not_called()
    assert snapshot(config) == before


def test_permitted_header_and_metadata_mentions_through_service_pipeline(workspace):
    config = workspace
    payload = definition()
    for location in LOCATIONS:
        comment_payload(payload, location)["Comment"] = (
            "This file is managed by keywharf\n\nmentions keywharf-owner in the middle"
        )
    write_json(config.host_repo_path / "config.json", [payload])
    assert validate_workspace(config).ok
    apply_selected_state(config)
    assert get_local_status(config, SERVER).status == "applied"
    assert render_selected_state(config).in_sync
    assert not apply_selected_state(config).changed


@pytest.mark.parametrize("separator", ["\r", "\u2028", "\v"])
def test_reserved_prefix_policy_retains_all_logical_line_checks(workspace, separator):
    payload = definition()
    payload["Comment"] = f"first{separator}KeYwHaRf-OwNeR: other-node"
    write_json(workspace.host_repo_path / "config.json", [payload])
    assert any("reserved" in e for e in validate_workspace(workspace).errors)
    host = ssh_host()
    host.comment = payload["Comment"]
    with pytest.raises(ValueError, match="reserved"):
        render_ssh_config([host])


def test_invalid_comment_main_entrypoint_has_no_traceback(workspace, monkeypatch, capsys):
    from keywharf.cli import main

    before = snapshot(workspace)
    monkeypatch.setattr(
        "sys.argv",
        [
            "keywharf",
            "--workspace",
            str(workspace.workspace_root),
            "repo",
            "host",
            "update",
            SERVER,
            "--comment",
            FORBIDDEN[0],
        ],
    )
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 1
    output = capsys.readouterr()
    assert "reserved" in output.err
    assert "Traceback" not in output.err
    assert snapshot(workspace) == before
