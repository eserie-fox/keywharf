from __future__ import annotations

import json
import shutil
from pathlib import Path

from git import Actor, Repo
from typer.testing import CliRunner

from keywharf.cli import app
from keywharf.domain.errors import KeywharfError
from tests.support import (
    host_repo_payload,
    host_shell_payload,
    load_config,
    make_workspace,
    read_json,
    selection_payload,
    state_payload,
    write_host_repo_config,
    write_identity_file,
    write_manager_config,
    write_state_file,
)

RUNNER = CliRunner()
GIT_ACTOR = Actor("Keywharf Tests", "tests@example.com")


def _create_bare_host_repo_remote(base_dir: Path) -> Path:
    if shutil.which("git") is None:
        raise RuntimeError("git is required for host repo sync tests")

    source_repo = base_dir / "source"
    source_repo.mkdir(parents=True)
    (source_repo / "config.json").write_text("[]\n", encoding="utf-8")
    (source_repo / ".gitignore").write_text("*.bak\n", encoding="utf-8")
    with Repo.init(source_repo, initial_branch="main") as repo:
        repo.index.add(["config.json", ".gitignore"])
        repo.index.commit("init", author=GIT_ACTOR, committer=GIT_ACTOR)

    remote_repo = base_dir / "remote.git"
    with Repo.init(remote_repo, bare=True, initial_branch="main"):
        pass
    with Repo(source_repo, search_parent_directories=False) as repo:
        origin = repo.create_remote("origin", str(remote_repo))
        origin.push("main:main")
    return remote_repo


def test_repo_init_bootstraps_local_host_repo_skeleton_without_git(
    tmp_path: Path,
) -> None:
    workspace_root = make_workspace(tmp_path)
    config_path = write_manager_config(workspace_root / "config.json")
    config = load_config(config_path, workspace_root=workspace_root)

    result = RUNNER.invoke(app, ["--config", str(config_path), "repo", "init"])

    assert result.exit_code == 0, result.output
    assert read_json(config.host_repo_path / "config.json") == []
    assert (config.host_repo_path / "keys").is_dir()
    assert (config.host_repo_path / ".gitignore").exists()
    assert not (config.host_repo_path / ".git").exists()


def test_repo_host_add_creates_shell_and_emits_guidance(tmp_path: Path) -> None:
    workspace_root = make_workspace(tmp_path)
    config_path = write_manager_config(workspace_root / "config.json")
    config = load_config(config_path, workspace_root=workspace_root)
    write_host_repo_config(config.host_repo_path, payload=[])

    add_result = RUNNER.invoke(
        app,
        [
            "--config",
            str(config_path),
            "repo",
            "host",
            "add",
            "demo",
            "--comment",
            "demo host",
        ],
    )
    list_result = RUNNER.invoke(
        app, ["--config", str(config_path), "repo", "host", "list", "--json"]
    )
    show_result = RUNNER.invoke(
        app,
        ["--config", str(config_path), "repo", "host", "show", "demo", "--json"],
    )

    assert add_result.exit_code == 0, add_result.output
    assert "Added host 'demo'" in add_result.output
    assert "has no endpoint or authentication options yet" in add_result.output
    assert "repo host endpoint add demo <endpoint_name> --hostname <host>" in add_result.output
    assert "repo host auth add demo <auth_name>" in add_result.output

    payload = read_json(config.host_repo_path / "config.json")
    assert payload == [{"ServerName": "demo", "Comment": "demo host"}]

    listed = json.loads(list_result.output)
    shown = json.loads(show_result.output)
    assert listed == payload
    assert shown == payload[0]


def test_repo_host_update_changes_top_level_fields_only(tmp_path: Path) -> None:
    workspace_root = make_workspace(tmp_path)
    config_path = write_manager_config(workspace_root / "config.json")
    config = load_config(config_path, workspace_root=workspace_root)
    write_host_repo_config(config.host_repo_path, payload=[host_shell_payload()])

    result = RUNNER.invoke(
        app,
        [
            "--config",
            str(config_path),
            "repo",
            "host",
            "update",
            "demo",
            "--new-name",
            "renamed",
            "--comment",
            "renamed host",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["subject"] == "host"
    assert payload["host"]["ServerName"] == "renamed"
    assert payload["host"]["Comment"] == "renamed host"
    assert read_json(config.host_repo_path / "config.json") == [
        {
            "ServerName": "renamed",
            "Comment": "renamed host",
            "ExtraConfig": [{"Key": "ProxyJump", "Value": "bastion", "Comment": "optional hop"}],
        }
    ]


def test_repo_host_update_rejects_comment_clear_conflict(tmp_path: Path) -> None:
    workspace_root = make_workspace(tmp_path)
    config_path = write_manager_config(workspace_root / "config.json")
    config = load_config(config_path, workspace_root=workspace_root)
    write_host_repo_config(config.host_repo_path, payload=[host_shell_payload()])

    result = RUNNER.invoke(
        app,
        [
            "--config",
            str(config_path),
            "repo",
            "host",
            "update",
            "demo",
            "--comment",
            "x",
            "--clear-comment",
        ],
    )

    assert result.exit_code == 2


def test_repo_host_remove_warns_when_local_state_becomes_stale(tmp_path: Path) -> None:
    workspace_root = make_workspace(tmp_path)
    config_path = write_manager_config(workspace_root / "config.json")
    config = load_config(config_path, workspace_root=workspace_root)
    write_identity_file(config.host_repo_path)
    write_host_repo_config(
        config.host_repo_path,
        payload=host_repo_payload(endpoint_name="public", auth_name="home"),
    )
    write_state_file(
        config.state_path,
        payload=state_payload(
            selected_hosts=[
                selection_payload(
                    server_name="demo",
                    endpoint_name="public",
                    authentication_name="home",
                )
            ]
        ),
    )

    result = RUNNER.invoke(
        app,
        ["--config", str(config_path), "repo", "host", "remove", "demo"],
    )

    assert result.exit_code == 0, result.output
    assert "WARNING: Local state still selects 'demo'" in result.output
    assert read_json(config.host_repo_path / "config.json") == []


def test_repo_host_endpoint_add_list_show_update_remove_and_persist_comment(
    tmp_path: Path,
) -> None:
    workspace_root = make_workspace(tmp_path)
    config_path = write_manager_config(workspace_root / "config.json")
    config = load_config(config_path, workspace_root=workspace_root)
    write_host_repo_config(config.host_repo_path, payload=[host_shell_payload()])

    add_result = RUNNER.invoke(
        app,
        [
            "--config",
            str(config_path),
            "repo",
            "host",
            "endpoint",
            "add",
            "demo",
            "public",
            "--hostname",
            "demo.example.com",
            "--comment",
            "edge endpoint",
        ],
    )
    list_result = RUNNER.invoke(
        app,
        [
            "--config",
            str(config_path),
            "repo",
            "host",
            "endpoint",
            "list",
            "demo",
            "--json",
        ],
    )
    show_result = RUNNER.invoke(
        app,
        [
            "--config",
            str(config_path),
            "repo",
            "host",
            "endpoint",
            "show",
            "demo",
            "public",
            "--json",
        ],
    )
    update_result = RUNNER.invoke(
        app,
        [
            "--config",
            str(config_path),
            "repo",
            "host",
            "endpoint",
            "update",
            "demo",
            "public",
            "--new-name",
            "private",
            "--hostname",
            "internal.example.com",
            "--port",
            "2222",
            "--comment",
            "internal endpoint",
            "--json",
        ],
    )
    remove_result = RUNNER.invoke(
        app,
        [
            "--config",
            str(config_path),
            "repo",
            "host",
            "endpoint",
            "remove",
            "demo",
            "private",
        ],
    )

    assert add_result.exit_code == 0, add_result.output
    assert "Added endpoint 'public' for host 'demo'" in add_result.output
    listed = json.loads(list_result.output)
    shown = json.loads(show_result.output)
    updated = json.loads(update_result.output)
    assert listed == [
        {
            "EndPointName": "public",
            "HostName": "demo.example.com",
            "Comment": "edge endpoint",
        }
    ]
    assert shown == listed[0]
    assert updated["endpoint"] == {
        "EndPointName": "private",
        "HostName": "internal.example.com",
        "Port": 2222,
        "Comment": "internal endpoint",
    }
    assert remove_result.exit_code == 0, remove_result.output
    assert read_json(config.host_repo_path / "config.json") == [
        {
            "ServerName": "demo",
            "Comment": "demo host",
            "ExtraConfig": [{"Key": "ProxyJump", "Value": "bastion", "Comment": "optional hop"}],
        }
    ]


def test_repo_host_endpoint_update_supports_clear_flags_and_warns_about_stale_selection(
    tmp_path: Path,
) -> None:
    workspace_root = make_workspace(tmp_path)
    config_path = write_manager_config(workspace_root / "config.json")
    config = load_config(config_path, workspace_root=workspace_root)
    write_identity_file(config.host_repo_path)
    write_host_repo_config(
        config.host_repo_path,
        payload=host_repo_payload(endpoint_name="public", auth_name="home"),
    )
    write_state_file(
        config.state_path,
        payload=state_payload(
            selected_hosts=[
                selection_payload(
                    server_name="demo",
                    endpoint_name="public",
                    authentication_name="home",
                )
            ]
        ),
    )

    result = RUNNER.invoke(
        app,
        [
            "--config",
            str(config_path),
            "repo",
            "host",
            "endpoint",
            "update",
            "demo",
            "public",
            "--new-name",
            "private",
            "--clear-port",
            "--clear-comment",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "WARNING: Local state still refers to endpoint 'public' for 'demo'" in result.output
    assert read_json(config.host_repo_path / "config.json")[0]["Endpoint"] == [
        {"EndPointName": "private", "HostName": "example.com"}
    ]


def test_repo_host_endpoint_update_rejects_port_clear_conflict(tmp_path: Path) -> None:
    workspace_root = make_workspace(tmp_path)
    config_path = write_manager_config(workspace_root / "config.json")
    config = load_config(config_path, workspace_root=workspace_root)
    write_host_repo_config(config.host_repo_path, payload=[host_shell_payload()])

    result = RUNNER.invoke(
        app,
        [
            "--config",
            str(config_path),
            "repo",
            "host",
            "endpoint",
            "add",
            "demo",
            "public",
            "--hostname",
            "demo.example.com",
        ],
    )
    assert result.exit_code == 0, result.output

    conflict_result = RUNNER.invoke(
        app,
        [
            "--config",
            str(config_path),
            "repo",
            "host",
            "endpoint",
            "update",
            "demo",
            "public",
            "--port",
            "22",
            "--clear-port",
        ],
    )

    assert conflict_result.exit_code == 2


def test_repo_host_auth_add_list_show_update_remove_and_persist_comment(
    tmp_path: Path,
) -> None:
    workspace_root = make_workspace(tmp_path)
    config_path = write_manager_config(workspace_root / "config.json")
    config = load_config(config_path, workspace_root=workspace_root)
    write_host_repo_config(config.host_repo_path, payload=[host_shell_payload()])
    write_identity_file(config.host_repo_path, "keys/id_home")
    write_identity_file(config.host_repo_path, "keys/id_work")

    add_result = RUNNER.invoke(
        app,
        [
            "--config",
            str(config_path),
            "repo",
            "host",
            "auth",
            "add",
            "demo",
            "home",
            "--user",
            "fox",
            "--identity-file",
            "keys/id_home",
            "--comment",
            "home key",
        ],
    )
    list_result = RUNNER.invoke(
        app,
        [
            "--config",
            str(config_path),
            "repo",
            "host",
            "auth",
            "list",
            "demo",
            "--json",
        ],
    )
    show_result = RUNNER.invoke(
        app,
        [
            "--config",
            str(config_path),
            "repo",
            "host",
            "auth",
            "show",
            "demo",
            "home",
            "--json",
        ],
    )
    update_result = RUNNER.invoke(
        app,
        [
            "--config",
            str(config_path),
            "repo",
            "host",
            "auth",
            "update",
            "demo",
            "home",
            "--new-name",
            "work",
            "--user",
            "ops",
            "--identity-file",
            "keys/id_work",
            "--comment",
            "work key",
            "--json",
        ],
    )
    remove_result = RUNNER.invoke(
        app,
        [
            "--config",
            str(config_path),
            "repo",
            "host",
            "auth",
            "remove",
            "demo",
            "work",
        ],
    )

    assert add_result.exit_code == 0, add_result.output
    assert "Added auth 'home' for host 'demo'" in add_result.output
    listed = json.loads(list_result.output)
    shown = json.loads(show_result.output)
    updated = json.loads(update_result.output)
    assert listed == [
        {
            "AuthenticationName": "home",
            "User": "fox",
            "IdentityFile": "keys/id_home",
            "Comment": "home key",
        }
    ]
    assert shown == listed[0]
    assert updated["auth"] == {
        "AuthenticationName": "work",
        "User": "ops",
        "IdentityFile": "keys/id_work",
        "Comment": "work key",
    }
    assert remove_result.exit_code == 0, remove_result.output
    assert read_json(config.host_repo_path / "config.json") == [
        {
            "ServerName": "demo",
            "Comment": "demo host",
            "ExtraConfig": [{"Key": "ProxyJump", "Value": "bastion", "Comment": "optional hop"}],
        }
    ]


def test_repo_host_auth_add_requires_user_or_identity_file(tmp_path: Path) -> None:
    workspace_root = make_workspace(tmp_path)
    config_path = write_manager_config(workspace_root / "config.json")
    config = load_config(config_path, workspace_root=workspace_root)
    write_host_repo_config(config.host_repo_path, payload=[host_shell_payload()])

    result = RUNNER.invoke(
        app,
        [
            "--config",
            str(config_path),
            "repo",
            "host",
            "auth",
            "add",
            "demo",
            "home",
        ],
    )

    assert result.exit_code == 1
    assert isinstance(result.exception, KeywharfError)
    assert "must set user or identity file" in str(result.exception)


def test_repo_host_auth_update_rejects_conflicts_and_empty_auth(tmp_path: Path) -> None:
    workspace_root = make_workspace(tmp_path)
    config_path = write_manager_config(workspace_root / "config.json")
    config = load_config(config_path, workspace_root=workspace_root)
    write_identity_file(config.host_repo_path)
    write_host_repo_config(
        config.host_repo_path,
        payload=[
            host_shell_payload(),
        ],
    )
    add_result = RUNNER.invoke(
        app,
        [
            "--config",
            str(config_path),
            "repo",
            "host",
            "auth",
            "add",
            "demo",
            "home",
            "--user",
            "fox",
        ],
    )
    assert add_result.exit_code == 0, add_result.output

    conflict_result = RUNNER.invoke(
        app,
        [
            "--config",
            str(config_path),
            "repo",
            "host",
            "auth",
            "update",
            "demo",
            "home",
            "--user",
            "ops",
            "--clear-user",
        ],
    )
    empty_result = RUNNER.invoke(
        app,
        [
            "--config",
            str(config_path),
            "repo",
            "host",
            "auth",
            "update",
            "demo",
            "home",
            "--clear-user",
            "--clear-identity-file",
        ],
    )

    assert conflict_result.exit_code == 2
    assert empty_result.exit_code == 1
    assert isinstance(empty_result.exception, KeywharfError)
    assert "must set user or identity file" in str(empty_result.exception)


def test_repo_host_auth_update_warns_when_selected_name_changes(tmp_path: Path) -> None:
    workspace_root = make_workspace(tmp_path)
    config_path = write_manager_config(workspace_root / "config.json")
    config = load_config(config_path, workspace_root=workspace_root)
    write_identity_file(config.host_repo_path)
    write_host_repo_config(
        config.host_repo_path,
        payload=host_repo_payload(endpoint_name="public", auth_name="home"),
    )
    write_state_file(
        config.state_path,
        payload=state_payload(
            selected_hosts=[
                selection_payload(
                    server_name="demo",
                    endpoint_name="public",
                    authentication_name="home",
                )
            ]
        ),
    )

    result = RUNNER.invoke(
        app,
        [
            "--config",
            str(config_path),
            "repo",
            "host",
            "auth",
            "update",
            "demo",
            "home",
            "--new-name",
            "work",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "WARNING: Local state still refers to authentication 'home' for 'demo'" in result.output


def test_repo_sync_errors_when_host_repo_remote_url_is_null(tmp_path: Path) -> None:
    workspace_root = make_workspace(tmp_path)
    config_path = write_manager_config(workspace_root / "config.json")

    result = RUNNER.invoke(app, ["--config", str(config_path), "repo", "sync"])

    assert result.exit_code == 1
    assert result.exception is not None
    assert "`host_repo_remote_url` is not configured" in str(result.exception)
    assert "repo init" in str(result.exception)


def test_repo_sync_clones_into_existing_empty_workspace_repo_directory(
    tmp_path: Path,
) -> None:
    remote_repo = _create_bare_host_repo_remote(tmp_path / "remote-source")
    workspace_root = make_workspace(tmp_path)
    config_path = write_manager_config(
        workspace_root / "config.json",
        host_repo_remote_url=str(remote_repo),
    )
    config = load_config(config_path, workspace_root=workspace_root)
    config.host_repo_path.mkdir(parents=True, exist_ok=False)

    result = RUNNER.invoke(app, ["--config", str(config_path), "repo", "sync"])

    assert result.exit_code == 0, result.output
    assert config.host_repo_path == (workspace_root / "repo").resolve()
    assert read_json(config.host_repo_path / "config.json") == []
    assert (config.host_repo_path / ".git").is_dir()
    assert f"Synced host repo into {config.host_repo_path}." in result.output


def test_repo_sync_fails_with_actionable_message_for_bootstrap_host_repo(
    tmp_path: Path,
) -> None:
    workspace_root = make_workspace(tmp_path)
    config_path = write_manager_config(
        workspace_root / "config.json",
        host_repo_remote_url="git@example.com:org/hosts.git",
    )

    init_result = RUNNER.invoke(app, ["--config", str(config_path), "repo", "init"])
    sync_result = RUNNER.invoke(app, ["--config", str(config_path), "repo", "sync"])

    assert init_result.exit_code == 0, init_result.output
    assert sync_result.exit_code == 1
    assert sync_result.exception is not None
    assert "local-first bootstrap" in str(sync_result.exception)
    assert "keywharf repo init" in str(sync_result.exception)
