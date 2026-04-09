from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from keywharf.cli import app
from keywharf.domain.errors import KeywharfError
from tests.support import (
    load_config,
    make_data_root,
    read_json,
    remote_repo_payload,
    selection_payload,
    state_payload,
    write_identity_file,
    write_manager_config,
    write_remote_repo_config,
    write_state_file,
)


RUNNER = CliRunner()


def test_remote_host_list_and_show_read_local_checkout_config(tmp_path: Path) -> None:
    data_root = make_data_root(tmp_path)
    config_path = write_manager_config(data_root / "config.json")
    config = load_config(config_path, data_root=data_root)
    repo_root = config.ssh_key_local_repo
    write_identity_file(repo_root)
    write_remote_repo_config(repo_root, payload=remote_repo_payload(endpoint_name="public", auth_name="home"))

    list_result = RUNNER.invoke(app, ["--config", str(config_path), "remote", "host", "list", "--json"])
    show_result = RUNNER.invoke(app, ["--config", str(config_path), "remote", "host", "show", "demo", "--json"])

    assert list_result.exit_code == 0, list_result.output
    assert show_result.exit_code == 0, show_result.output
    listed = json.loads(list_result.output)
    shown = json.loads(show_result.output)
    assert listed[0]["ServerName"] == "demo"
    assert shown["ServerName"] == "demo"


def test_remote_host_add_writes_structured_host_entry(tmp_path: Path) -> None:
    data_root = make_data_root(tmp_path)
    config_path = write_manager_config(data_root / "config.json")
    config = load_config(config_path, data_root=data_root)
    repo_root = config.ssh_key_local_repo
    write_identity_file(repo_root)
    write_remote_repo_config(repo_root, payload=[])

    result = RUNNER.invoke(
        app,
        [
            "--config",
            str(config_path),
            "remote",
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
    payload = read_json(repo_root / "config.json")
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


def test_remote_host_add_rejects_duplicate_server_name(tmp_path: Path) -> None:
    data_root = make_data_root(tmp_path)
    config_path = write_manager_config(data_root / "config.json")
    config = load_config(config_path, data_root=data_root)
    repo_root = config.ssh_key_local_repo
    write_identity_file(repo_root)
    write_remote_repo_config(repo_root, payload=remote_repo_payload(endpoint_name="public", auth_name="home"))

    result = RUNNER.invoke(
        app,
        [
            "--config",
            str(config_path),
            "remote",
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


def test_remote_host_update_requires_target_selectors_for_multi_option_hosts(tmp_path: Path) -> None:
    data_root = make_data_root(tmp_path)
    config_path = write_manager_config(data_root / "config.json")
    config = load_config(config_path, data_root=data_root)
    repo_root = config.ssh_key_local_repo
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
        [
            "--config",
            str(config_path),
            "remote",
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


def test_remote_host_update_and_remove_warn_when_local_state_becomes_stale(tmp_path: Path) -> None:
    data_root = make_data_root(tmp_path)
    config_path = write_manager_config(data_root / "config.json")
    config = load_config(config_path, data_root=data_root)
    repo_root = config.ssh_key_local_repo
    write_identity_file(repo_root)
    write_remote_repo_config(repo_root, payload=remote_repo_payload(endpoint_name="public", auth_name="home"))
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
            "remote",
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
            "remote",
            "host",
            "remove",
            "renamed",
            "--json",
        ],
    )

    assert update_result.exit_code == 0, update_result.output
    assert "WARNING: Local state still refers to remote host 'demo'" in update_result.output
    assert remove_result.exit_code == 0, remove_result.output
    payload = json.loads(remove_result.output)
    assert payload["removed_name"] == "renamed"
    assert payload["warnings"] == []
    assert read_json(repo_root / "config.json") == []
