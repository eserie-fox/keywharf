from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from ssh_manager.cli import app
from ssh_manager.runtime.config import load_manager_config
from tests.support import (
    make_data_root,
    remote_repo_payload,
    write_identity_file,
    write_manager_config,
    write_remote_repo_config,
)


RUNNER = CliRunner()


def test_select_writes_state_and_upserts_existing_selection(tmp_path: Path) -> None:
    data_root = make_data_root(tmp_path)
    config_path = write_manager_config(data_root / "config.json")
    config = load_manager_config(config_path, data_root=data_root)
    repo_root = data_root / "repos" / "keys"
    write_identity_file(repo_root, "keys/id_home")
    write_identity_file(repo_root, "keys/id_work")
    write_remote_repo_config(
        repo_root,
        payload=remote_repo_payload(
            endpoints=[
                {"EndPointName": "public", "HostName": "public.example.com", "Port": 22},
                {"EndPointName": "private", "HostName": "private.example.com", "Port": 22},
            ],
            authentications=[
                {
                    "AuthenticationName": "home",
                    "User": "fox",
                    "IdentityFile": "keys/id_home",
                },
                {
                    "AuthenticationName": "work",
                    "User": "fox",
                    "IdentityFile": "keys/id_work",
                },
            ],
        ),
    )

    first = RUNNER.invoke(
        app,
        ["--config", str(config_path), "select", "demo", "--endpoint", "public", "--auth", "home"],
    )
    second = RUNNER.invoke(
        app,
        ["--config", str(config_path), "select", "demo", "--endpoint", "private", "--auth", "work"],
    )

    assert first.exit_code == 0, first.output
    assert second.exit_code == 0, second.output
    payload = json.loads(config.state_path.read_text(encoding="utf-8"))
    assert payload["selected_hosts"] == [
        {
            "server_name": "demo",
            "endpoint_name": "private",
            "authentication_name": "work",
        }
    ]
    assert not config.managed_config_path.exists()


def test_deselect_only_updates_state(tmp_path: Path) -> None:
    data_root = make_data_root(tmp_path)
    config_path = write_manager_config(data_root / "config.json")
    config = load_manager_config(config_path, data_root=data_root)
    repo_root = data_root / "repos" / "keys"
    write_identity_file(repo_root)
    write_remote_repo_config(
        repo_root,
        payload=remote_repo_payload(endpoint_name="public", auth_name="home"),
    )
    RUNNER.invoke(
        app,
        ["--config", str(config_path), "select", "demo", "--endpoint", "public", "--auth", "home"],
    )

    result = RUNNER.invoke(app, ["--config", str(config_path), "deselect", "demo"])

    assert result.exit_code == 0, result.output
    payload = json.loads(config.state_path.read_text(encoding="utf-8"))
    assert payload["selected_hosts"] == []
    assert not config.managed_config_path.exists()


def test_compatibility_add_and_remove_map_to_state_only(tmp_path: Path) -> None:
    data_root = make_data_root(tmp_path)
    config_path = write_manager_config(data_root / "config.json")
    config = load_manager_config(config_path, data_root=data_root)
    repo_root = data_root / "repos" / "keys"
    write_identity_file(repo_root, "keys/id_home")
    write_identity_file(repo_root, "keys/id_work")
    write_remote_repo_config(
        repo_root,
        payload=remote_repo_payload(
            endpoints=[
                {"EndPointName": "public", "HostName": "public.example.com", "Port": 22},
                {"EndPointName": "private", "HostName": "private.example.com", "Port": 22},
            ],
            authentications=[
                {
                    "AuthenticationName": "home",
                    "User": "fox",
                    "IdentityFile": "keys/id_home",
                },
                {
                    "AuthenticationName": "work",
                    "User": "fox",
                    "IdentityFile": "keys/id_work",
                },
            ],
        ),
    )

    add_result = RUNNER.invoke(
        app,
        [
            "--config",
            str(config_path),
            "add",
            "demo",
            "--endpoint-id",
            "1",
            "--auth-id",
            "1",
            "--non-interactive",
        ],
    )
    remove_result = RUNNER.invoke(
        app,
        ["--config", str(config_path), "remove", "demo", "--yes"],
    )

    assert add_result.exit_code == 0, add_result.output
    assert "Prefer 'ssh-manager select'" in add_result.output
    assert remove_result.exit_code == 0, remove_result.output
    assert "Prefer 'ssh-manager deselect'" in remove_result.output
    assert not config.managed_config_path.exists()
