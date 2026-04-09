from __future__ import annotations

from pathlib import Path

from keywharf.services.validate import validate_workspace
from tests.support import (
    load_config,
    make_data_root,
    remote_repo_payload,
    selection_payload,
    state_payload,
    write_identity_file,
    write_manager_config,
    write_remote_repo_config,
    write_state_file,
)


def test_validate_warns_when_include_is_missing_but_workspace_is_otherwise_valid(tmp_path: Path) -> None:
    data_root = make_data_root(tmp_path)
    config_path = write_manager_config(data_root / "config.json")
    config = load_config(config_path, data_root=data_root)
    repo_root = data_root / "repos" / "keys"
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

    result = validate_workspace(config)

    assert result.ok is True
    assert any("install-include" in warning for warning in result.warnings)


def test_validate_rejects_multiple_unnamed_options(tmp_path: Path) -> None:
    data_root = make_data_root(tmp_path)
    config_path = write_manager_config(data_root / "config.json")
    config = load_config(config_path, data_root=data_root)
    repo_root = data_root / "repos" / "keys"
    write_identity_file(repo_root, "keys/id_demo")
    write_identity_file(repo_root, "keys/id_demo_2")
    write_remote_repo_config(
        repo_root,
        payload=remote_repo_payload(
            endpoints=[
                {"HostName": "a.example.com", "Port": 22},
                {"HostName": "b.example.com", "Port": 2222},
            ],
            authentications=[
                {"User": "fox", "IdentityFile": "keys/id_demo"},
                {"User": "fox", "IdentityFile": "keys/id_demo_2"},
            ],
        ),
    )

    result = validate_workspace(config)

    assert result.ok is False
    assert any("EndPointName" in error for error in result.errors)
    assert any("AuthenticationName" in error for error in result.errors)


def test_validate_rejects_duplicate_server_and_selector_names(tmp_path: Path) -> None:
    data_root = make_data_root(tmp_path)
    config_path = write_manager_config(data_root / "config.json")
    config = load_config(config_path, data_root=data_root)
    repo_root = data_root / "repos" / "keys"
    write_identity_file(repo_root, "keys/id_demo")
    write_identity_file(repo_root, "keys/id_demo_2")
    write_remote_repo_config(
        repo_root,
        payload=[
            remote_repo_payload(server_name="demo", endpoint_name="public", auth_name="home")[0],
            remote_repo_payload(
                server_name="demo",
                endpoints=[
                    {"EndPointName": "public", "HostName": "b.example.com", "Port": 22},
                    {"EndPointName": "public", "HostName": "c.example.com", "Port": 23},
                ],
                authentications=[
                    {"AuthenticationName": "home", "User": "fox", "IdentityFile": "keys/id_demo"},
                    {"AuthenticationName": "home", "User": "fox", "IdentityFile": "keys/id_demo_2"},
                ],
            )[0],
        ],
    )

    result = validate_workspace(config)

    assert result.ok is False
    assert any("Duplicate ServerName 'demo'" in error for error in result.errors)
    assert any("duplicate EndPointName 'public'" in error for error in result.errors)
    assert any("duplicate AuthenticationName 'home'" in error for error in result.errors)


def test_validate_rejects_state_reference_to_missing_selector(tmp_path: Path) -> None:
    data_root = make_data_root(tmp_path)
    config_path = write_manager_config(data_root / "config.json")
    config = load_config(config_path, data_root=data_root)
    repo_root = data_root / "repos" / "keys"
    write_identity_file(repo_root)
    write_remote_repo_config(repo_root, payload=remote_repo_payload(endpoint_name="public", auth_name="home"))
    write_state_file(
        config.state_path,
        payload=state_payload(
            selected_hosts=[
                selection_payload(server_name="demo", endpoint_name="missing", authentication_name="home")
            ]
        ),
    )

    result = validate_workspace(config)

    assert result.ok is False
    assert any("no endpoint named 'missing'" in error for error in result.errors)


def test_validate_rejects_null_selector_after_remote_gains_multiple_options(tmp_path: Path) -> None:
    data_root = make_data_root(tmp_path)
    config_path = write_manager_config(data_root / "config.json")
    config = load_config(config_path, data_root=data_root)
    repo_root = data_root / "repos" / "keys"
    write_identity_file(repo_root, "keys/id_demo")
    write_identity_file(repo_root, "keys/id_demo_2")
    write_remote_repo_config(
        repo_root,
        payload=remote_repo_payload(
            endpoints=[
                {"EndPointName": "public", "HostName": "a.example.com", "Port": 22},
                {"EndPointName": "private", "HostName": "b.example.com", "Port": 22},
            ],
            authentications=[
                {"AuthenticationName": "home", "User": "fox", "IdentityFile": "keys/id_demo"},
                {"AuthenticationName": "work", "User": "fox", "IdentityFile": "keys/id_demo_2"},
            ],
        ),
    )
    write_state_file(
        config.state_path,
        payload=state_payload(
            selected_hosts=[selection_payload(server_name="demo", endpoint_name=None, authentication_name=None)]
        ),
    )

    result = validate_workspace(config)

    assert result.ok is False
    assert any("multiple endpoint options" in error for error in result.errors)
    assert any("multiple authentication options" in error for error in result.errors)

