from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess

from typer.testing import CliRunner

from keywharf.cli import app
from keywharf.domain.errors import KeywharfError
from tests.support import (
    host_repo_payload,
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


def _run_git(args: list[str], *, cwd: Path | None = None) -> None:
    subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )


def _create_bare_host_repo_remote(base_dir: Path) -> Path:
    if shutil.which("git") is None:
        raise RuntimeError("git is required for host repo sync tests")

    source_repo = base_dir / "source"
    source_repo.mkdir(parents=True)
    _run_git(["init"], cwd=source_repo)
    _run_git(["config", "user.email", "tests@example.com"], cwd=source_repo)
    _run_git(["config", "user.name", "tests"], cwd=source_repo)
    (source_repo / "config.json").write_text("[]\n", encoding="utf-8")
    (source_repo / ".gitignore").write_text("*.bak\n", encoding="utf-8")
    _run_git(["add", "config.json", ".gitignore"], cwd=source_repo)
    _run_git(["commit", "-m", "init"], cwd=source_repo)

    remote_repo = base_dir / "remote.git"
    _run_git(["clone", "--bare", str(source_repo), str(remote_repo)])
    return remote_repo


def test_repo_host_list_and_show_read_host_repo_config(tmp_path: Path) -> None:
    workspace_root = make_workspace(tmp_path)
    config_path = write_manager_config(workspace_root / "config.json")
    config = load_config(config_path, workspace_root=workspace_root)
    host_repo_path = config.host_repo_path
    write_identity_file(host_repo_path)
    write_host_repo_config(host_repo_path, payload=host_repo_payload(endpoint_name="public", auth_name="home"))

    list_result = RUNNER.invoke(app, ["--config", str(config_path), "repo", "host", "list", "--json"])
    show_result = RUNNER.invoke(app, ["--config", str(config_path), "repo", "host", "show", "demo", "--json"])

    assert list_result.exit_code == 0, list_result.output
    assert show_result.exit_code == 0, show_result.output
    listed = json.loads(list_result.output)
    shown = json.loads(show_result.output)
    assert listed[0]["ServerName"] == "demo"
    assert shown["ServerName"] == "demo"


def test_repo_init_bootstraps_local_host_repo_and_allows_host_add(tmp_path: Path) -> None:
    workspace_root = make_workspace(tmp_path)
    config_path = write_manager_config(workspace_root / "config.json")
    config = load_config(config_path, workspace_root=workspace_root)

    init_result = RUNNER.invoke(app, ["--config", str(config_path), "repo", "init"])

    assert init_result.exit_code == 0, init_result.output
    assert read_json(config.host_repo_path / "config.json") == []
    assert (config.host_repo_path / "keys").is_dir()
    assert (config.host_repo_path / ".gitignore").exists()
    assert not (config.host_repo_path / ".git").exists()

    write_identity_file(config.host_repo_path)
    add_result = RUNNER.invoke(
        app,
        [
            "--config",
            str(config_path),
            "repo",
            "host",
            "add",
            "demo",
            "--hostname",
            "demo.example.com",
            "--user",
            "fox",
            "--identity-file",
            "keys/id_demo",
            "--endpoint-name",
            "public",
            "--auth-name",
            "home",
        ],
    )

    assert add_result.exit_code == 0, add_result.output
    assert read_json(config.host_repo_path / "config.json")[0]["ServerName"] == "demo"


def test_repo_host_add_writes_structured_host_entry(tmp_path: Path) -> None:
    workspace_root = make_workspace(tmp_path)
    config_path = write_manager_config(workspace_root / "config.json")
    config = load_config(config_path, workspace_root=workspace_root)
    host_repo_path = config.host_repo_path
    write_identity_file(host_repo_path)
    write_host_repo_config(host_repo_path, payload=[])

    result = RUNNER.invoke(
        app,
        [
            "--config",
            str(config_path),
            "repo",
            "host",
            "add",
            "demo",
            "--hostname",
            "demo.example.com",
            "--user",
            "fox",
            "--identity-file",
            "keys/id_demo",
            "--endpoint-name",
            "public",
            "--auth-name",
            "home",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = read_json(host_repo_path / "config.json")
    assert payload == [
        {
            "ServerName": "demo",
            "Endpoint": [
                {
                    "EndPointName": "public",
                    "HostName": "demo.example.com",
                    "Port": 22,
                }
            ],
            "Authentication": [
                {
                    "AuthenticationName": "home",
                    "User": "fox",
                    "IdentityFile": "keys/id_demo",
                }
            ],
        }
    ]


def test_repo_host_add_rejects_duplicate_server_name(tmp_path: Path) -> None:
    workspace_root = make_workspace(tmp_path)
    config_path = write_manager_config(workspace_root / "config.json")
    config = load_config(config_path, workspace_root=workspace_root)
    host_repo_path = config.host_repo_path
    write_identity_file(host_repo_path)
    write_host_repo_config(host_repo_path, payload=host_repo_payload(endpoint_name="public", auth_name="home"))

    result = RUNNER.invoke(
        app,
        [
            "--config",
            str(config_path),
            "repo",
            "host",
            "add",
            "demo",
            "--hostname",
            "other.example.com",
            "--user",
            "fox",
            "--identity-file",
            "keys/id_demo",
        ],
    )

    assert result.exit_code == 1
    assert isinstance(result.exception, KeywharfError)
    assert "already exists" in str(result.exception)


def test_repo_host_update_requires_target_selectors_for_multi_option_hosts(tmp_path: Path) -> None:
    workspace_root = make_workspace(tmp_path)
    config_path = write_manager_config(workspace_root / "config.json")
    config = load_config(config_path, workspace_root=workspace_root)
    host_repo_path = config.host_repo_path
    write_identity_file(host_repo_path, "keys/id_home")
    write_identity_file(host_repo_path, "keys/id_work")
    write_host_repo_config(
        host_repo_path,
        payload=host_repo_payload(
            endpoints=[
                {"EndPointName": "public", "HostName": "public.example.com", "Port": 22},
                {"EndPointName": "private", "HostName": "private.example.com", "Port": 22},
            ],
            authentications=[
                {"AuthenticationName": "home", "User": "fox", "IdentityFile": "keys/id_home"},
                {"AuthenticationName": "work", "User": "fox", "IdentityFile": "keys/id_work"},
            ],
        ),
    )

    result = RUNNER.invoke(
        app,
        [
            "--config",
            str(config_path),
            "repo",
            "host",
            "update",
            "demo",
            "--hostname",
            "updated.example.com",
        ],
    )

    assert result.exit_code == 1
    assert isinstance(result.exception, KeywharfError)
    assert "--target-endpoint" in str(result.exception)


def test_repo_host_update_and_remove_warn_when_local_state_becomes_stale(tmp_path: Path) -> None:
    workspace_root = make_workspace(tmp_path)
    config_path = write_manager_config(workspace_root / "config.json")
    config = load_config(config_path, workspace_root=workspace_root)
    host_repo_path = config.host_repo_path
    write_identity_file(host_repo_path)
    write_host_repo_config(host_repo_path, payload=host_repo_payload(endpoint_name="public", auth_name="home"))
    write_state_file(
        config.state_path,
        payload=state_payload(
            selected_hosts=[
                selection_payload(server_name="demo", endpoint_name="public", authentication_name="home")
            ]
        ),
    )

    update_result = RUNNER.invoke(
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
            "--auth-name",
            "work",
        ],
    )
    remove_result = RUNNER.invoke(
        app,
        [
            "--config",
            str(config_path),
            "repo",
            "host",
            "remove",
            "renamed",
            "--json",
        ],
    )

    assert update_result.exit_code == 0, update_result.output
    assert "WARNING: Local state still refers to host 'demo'" in update_result.output
    assert remove_result.exit_code == 0, remove_result.output
    payload = json.loads(remove_result.output)
    assert payload["removed_name"] == "renamed"
    assert payload["warnings"] == []
    assert read_json(host_repo_path / "config.json") == []


def test_repo_sync_errors_when_host_repo_remote_url_is_null(tmp_path: Path) -> None:
    workspace_root = make_workspace(tmp_path)
    config_path = write_manager_config(workspace_root / "config.json")

    result = RUNNER.invoke(app, ["--config", str(config_path), "repo", "sync"])

    assert result.exit_code == 1
    assert result.exception is not None
    assert "`host_repo_remote_url` is not configured" in str(result.exception)
    assert "repo init" in str(result.exception)


def test_repo_sync_clones_into_existing_empty_workspace_repo_directory(tmp_path: Path) -> None:
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


def test_repo_sync_fails_with_actionable_message_for_bootstrap_host_repo(tmp_path: Path) -> None:
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
