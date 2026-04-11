from __future__ import annotations

from pathlib import Path

from keywharf.services.render import render_selected_state
from tests.support import (
    host_repo_payload,
    load_config,
    make_workspace,
    selection_payload,
    state_payload,
    write_identity_file,
    write_manager_config,
    write_host_repo_config,
    write_state_file,
)


def test_render_produces_preview_without_writing_files(tmp_path: Path) -> None:
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

    result = render_selected_state(config)

    assert "Host demo" in result.content
    assert str(config.managed_keys_dir / "demo" / "id_demo") in result.content
    assert not config.managed_config_path.exists()
    assert list(config.managed_keys_dir.rglob("*")) == []


def test_render_stable_selectors_do_not_drift_when_host_repo_order_changes(tmp_path: Path) -> None:
    workspace_root = make_workspace(tmp_path)
    config_path = write_manager_config(workspace_root / "config.json")
    config = load_config(config_path, workspace_root=workspace_root)
    host_repo_path = config.host_repo_path
    write_identity_file(host_repo_path, "keys/id_home")
    write_identity_file(host_repo_path, "keys/id_work")
    write_state_file(
        config.state_path,
        payload=state_payload(
            selected_hosts=[
                selection_payload(server_name="demo", endpoint_name="public", authentication_name="work")
            ]
        ),
    )
    first_payload = host_repo_payload(
        endpoints=[
            {"EndPointName": "public", "HostName": "public.example.com", "Port": 22},
            {"EndPointName": "private", "HostName": "private.example.com", "Port": 22},
        ],
        authentications=[
            {"AuthenticationName": "home", "User": "fox", "IdentityFile": "keys/id_home"},
            {"AuthenticationName": "work", "User": "fox", "IdentityFile": "keys/id_work"},
        ],
    )
    write_host_repo_config(host_repo_path, payload=first_payload)
    first_result = render_selected_state(config)

    second_payload = host_repo_payload(
        endpoints=list(reversed(first_payload[0]["Endpoint"])),
        authentications=list(reversed(first_payload[0]["Authentication"])),
    )
    write_host_repo_config(host_repo_path, payload=second_payload)
    second_result = render_selected_state(config)

    assert first_result.content == second_result.content
    assert first_result.resolved_selections[0].endpoint.name == "public"
    assert second_result.resolved_selections[0].authentication.name == "work"
