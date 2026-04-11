from __future__ import annotations

from pathlib import Path

from keywharf.services.validate import validate_workspace
from tests.support import (
    auth_payload,
    endpoint_payload,
    host_repo_payload,
    host_shell_payload,
    load_config,
    make_workspace,
    selection_payload,
    state_payload,
    write_identity_file,
    write_manager_config,
    write_host_repo_config,
    write_state_file,
)


def test_validate_warns_when_include_is_missing_but_workspace_is_otherwise_valid(tmp_path: Path) -> None:
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

    result = validate_workspace(config)

    assert result.ok is True
    assert any("install-include" in warning for warning in result.warnings)


def test_validate_reports_host_without_endpoint_options(tmp_path: Path) -> None:
    workspace_root = make_workspace(tmp_path)
    config_path = write_manager_config(workspace_root / "config.json")
    config = load_config(config_path, workspace_root=workspace_root)
    write_identity_file(config.host_repo_path)
    write_host_repo_config(
        config.host_repo_path,
        payload=[
            {
                **host_shell_payload(),
                "Authentication": [auth_payload(name="home", identity_file="keys/id_demo")],
            }
        ],
    )

    result = validate_workspace(config)

    assert result.ok is False
    assert result.errors[0] == "Host 'demo' has no endpoint options."
    assert result.errors[-1].startswith("Add missing options with ")


def test_validate_reports_host_without_authentication_options(tmp_path: Path) -> None:
    workspace_root = make_workspace(tmp_path)
    config_path = write_manager_config(workspace_root / "config.json")
    config = load_config(config_path, workspace_root=workspace_root)
    write_host_repo_config(
        config.host_repo_path,
        payload=[
            {
                **host_shell_payload(),
                "Endpoint": [endpoint_payload(name="public", hostname="demo.example.com")],
            }
        ],
    )

    result = validate_workspace(config)

    assert result.ok is False
    assert result.errors[0] == "Host 'demo' has no authentication options."
    assert result.errors[-1].startswith("Add missing options with ")


def test_validate_reports_host_without_endpoint_or_authentication_options(tmp_path: Path) -> None:
    workspace_root = make_workspace(tmp_path)
    config_path = write_manager_config(workspace_root / "config.json")
    config = load_config(config_path, workspace_root=workspace_root)
    write_host_repo_config(config.host_repo_path, payload=[host_shell_payload()])

    result = validate_workspace(config)

    assert result.ok is False
    assert result.errors[0] == "Host 'demo' has no endpoint or authentication options."
    assert result.errors[-1].startswith("Add missing options with ")


def test_validate_reports_all_incomplete_hosts_once_with_one_guidance_line(tmp_path: Path) -> None:
    workspace_root = make_workspace(tmp_path)
    config_path = write_manager_config(workspace_root / "config.json")
    config = load_config(config_path, workspace_root=workspace_root)
    write_identity_file(config.host_repo_path)
    write_host_repo_config(
        config.host_repo_path,
        payload=[
            {
                **host_shell_payload(server_name="missing-endpoint"),
                "Authentication": [auth_payload(name="home", identity_file="keys/id_demo")],
            },
            {
                **host_shell_payload(server_name="missing-auth"),
                "Endpoint": [endpoint_payload(name="public", hostname="auth.example.com")],
            },
            host_shell_payload(server_name="missing-both"),
        ],
    )

    result = validate_workspace(config)

    assert result.ok is False
    assert "Host 'missing-endpoint' has no endpoint options." in result.errors
    assert "Host 'missing-auth' has no authentication options." in result.errors
    assert "Host 'missing-both' has no endpoint or authentication options." in result.errors
    assert sum(1 for item in result.errors if item.startswith("Add missing options with ")) == 1


def test_validate_rejects_multiple_unnamed_options(tmp_path: Path) -> None:
    workspace_root = make_workspace(tmp_path)
    config_path = write_manager_config(workspace_root / "config.json")
    config = load_config(config_path, workspace_root=workspace_root)
    host_repo_path = config.host_repo_path
    write_identity_file(host_repo_path, "keys/id_demo")
    write_identity_file(host_repo_path, "keys/id_demo_2")
    write_host_repo_config(
        host_repo_path,
        payload=host_repo_payload(
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
    workspace_root = make_workspace(tmp_path)
    config_path = write_manager_config(workspace_root / "config.json")
    config = load_config(config_path, workspace_root=workspace_root)
    host_repo_path = config.host_repo_path
    write_identity_file(host_repo_path, "keys/id_demo")
    write_identity_file(host_repo_path, "keys/id_demo_2")
    write_host_repo_config(
        host_repo_path,
        payload=[
            host_repo_payload(server_name="demo", endpoint_name="public", auth_name="home")[0],
            host_repo_payload(
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
                selection_payload(server_name="demo", endpoint_name="missing", authentication_name="home")
            ]
        ),
    )

    result = validate_workspace(config)

    assert result.ok is False
    assert any("no endpoint named 'missing'" in error for error in result.errors)


def test_validate_rejects_null_selector_after_host_repo_gains_multiple_options(tmp_path: Path) -> None:
    workspace_root = make_workspace(tmp_path)
    config_path = write_manager_config(workspace_root / "config.json")
    config = load_config(config_path, workspace_root=workspace_root)
    host_repo_path = config.host_repo_path
    write_identity_file(host_repo_path, "keys/id_demo")
    write_identity_file(host_repo_path, "keys/id_demo_2")
    write_host_repo_config(
        host_repo_path,
        payload=host_repo_payload(
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


def test_validate_skips_duplicate_selection_errors_for_incomplete_selected_host(tmp_path: Path) -> None:
    workspace_root = make_workspace(tmp_path)
    config_path = write_manager_config(workspace_root / "config.json")
    config = load_config(config_path, workspace_root=workspace_root)
    write_host_repo_config(config.host_repo_path, payload=[host_shell_payload()])
    write_state_file(
        config.state_path,
        payload=state_payload(selected_hosts=[selection_payload(server_name="demo")]),
    )

    result = validate_workspace(config)

    assert result.ok is False
    assert result.errors.count("Host 'demo' has no endpoint or authentication options.") == 1
