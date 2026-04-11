from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from keywharf.cli import app
from tests.support import (
    host_repo_payload,
    host_shell_payload,
    load_config,
    make_workspace,
    read_json,
    selection_payload,
    state_payload,
    write_identity_file,
    write_manager_config,
    write_host_repo_config,
    write_state_file,
)


RUNNER = CliRunner()


def test_select_writes_state_and_upserts_existing_selection(tmp_path: Path) -> None:
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


def test_select_uses_stable_names_not_array_indexes(tmp_path: Path) -> None:
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
        ["--config", str(config_path), "select", "demo", "--endpoint", "private", "--auth", "work"],
    )

    assert result.exit_code == 0, result.output
    assert read_json(config.state_path)["selected_hosts"][0] == {
        "server_name": "demo",
        "endpoint_name": "private",
        "authentication_name": "work",
    }


def test_deselect_only_updates_state(tmp_path: Path) -> None:
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

    result = RUNNER.invoke(app, ["--config", str(config_path), "deselect", "demo"])

    assert result.exit_code == 0, result.output
    assert read_json(config.state_path)["selected_hosts"] == []
    assert not config.managed_config_path.exists()


def test_select_rejects_host_without_endpoint_options(tmp_path: Path) -> None:
    workspace_root = make_workspace(tmp_path)
    config_path = write_manager_config(workspace_root / "config.json")
    config = load_config(config_path, workspace_root=workspace_root)
    write_identity_file(config.host_repo_path)
    write_host_repo_config(
        config.host_repo_path,
        payload=[
            {
                **host_shell_payload(),
                "Authentication": [{"AuthenticationName": "home", "User": "fox", "IdentityFile": "keys/id_demo"}],
            }
        ],
    )

    result = RUNNER.invoke(app, ["--config", str(config_path), "select", "demo", "--auth", "home"])

    assert result.exit_code == 1
    assert "Host 'demo' has no endpoint options." in str(result.exception)
    assert "repo host endpoint add demo <endpoint_name> --hostname <host>" in str(result.exception)


def test_select_rejects_host_without_authentication_options(tmp_path: Path) -> None:
    workspace_root = make_workspace(tmp_path)
    config_path = write_manager_config(workspace_root / "config.json")
    config = load_config(config_path, workspace_root=workspace_root)
    write_host_repo_config(
        config.host_repo_path,
        payload=[
            {
                **host_shell_payload(),
                "Endpoint": [{"EndPointName": "public", "HostName": "demo.example.com"}],
            }
        ],
    )

    result = RUNNER.invoke(app, ["--config", str(config_path), "select", "demo", "--endpoint", "public"])

    assert result.exit_code == 1
    assert "Host 'demo' has no authentication options." in str(result.exception)
    assert "repo host auth add demo <auth_name>" in str(result.exception)


def test_select_rejects_host_without_endpoint_or_authentication_options(tmp_path: Path) -> None:
    workspace_root = make_workspace(tmp_path)
    config_path = write_manager_config(workspace_root / "config.json")
    config = load_config(config_path, workspace_root=workspace_root)
    write_host_repo_config(config.host_repo_path, payload=[host_shell_payload()])

    result = RUNNER.invoke(app, ["--config", str(config_path), "select", "demo"])

    assert result.exit_code == 1
    assert "Host 'demo' has no endpoint or authentication options." in str(result.exception)
    assert "repo host endpoint add demo <endpoint_name> --hostname <host>" in str(result.exception)
    assert "repo host auth add demo <auth_name>" in str(result.exception)
