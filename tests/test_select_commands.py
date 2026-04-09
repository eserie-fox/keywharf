from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from ssh_manager.cli import app
from tests.support import (
    load_config,
    make_data_root,
    read_json,
    remote_repo_payload,
    write_identity_file,
    write_manager_config,
    write_remote_repo_config,
)


RUNNER = CliRunner()


def test_select_writes_state_and_upserts_existing_selection(tmp_path: Path) -> None:
    data_root = make_data_root(tmp_path)
    config_path = write_manager_config(data_root / "config.json")
    config = load_config(config_path, data_root=data_root)
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
                {"AuthenticationName": "home", "User": "fox", "IdentityFile": "keys/id_home"},
                {"AuthenticationName": "work", "User": "fox", "IdentityFile": "keys/id_work"},
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
    assert read_json(config.state_path)["selected_hosts"] == [
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
    config = load_config(config_path, data_root=data_root)
    repo_root = data_root / "repos" / "keys"
    write_identity_file(repo_root)
    write_remote_repo_config(repo_root, payload=remote_repo_payload(endpoint_name="public", auth_name="home"))
    RUNNER.invoke(
        app,
        ["--config", str(config_path), "select", "demo", "--endpoint", "public", "--auth", "home"],
    )

    result = RUNNER.invoke(app, ["--config", str(config_path), "deselect", "demo"])

    assert result.exit_code == 0, result.output
    assert read_json(config.state_path)["selected_hosts"] == []
    assert not config.managed_config_path.exists()


def test_select_uses_stable_names_not_array_indexes(tmp_path: Path) -> None:
    data_root = make_data_root(tmp_path)
    config_path = write_manager_config(data_root / "config.json")
    config = load_config(config_path, data_root=data_root)
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
                {"AuthenticationName": "home", "User": "fox", "IdentityFile": "keys/id_home"},
                {"AuthenticationName": "work", "User": "fox", "IdentityFile": "keys/id_work"},
            ],
        ),
    )

    result = RUNNER.invoke(
        app,
        ["--config", str(config_path), "select", "demo", "--endpoint", "private", "--auth", "work"],
    )

    assert result.exit_code == 0, result.output
    assert read_json(config.state_path)["selected_hosts"][0] == {
        "server_name": "demo",
        "endpoint_name": "private",
        "authentication_name": "work",
    }

