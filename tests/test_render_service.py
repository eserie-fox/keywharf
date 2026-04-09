from __future__ import annotations

from pathlib import Path

from ssh_manager.runtime.config import load_manager_config
from ssh_manager.services.render import render_selected_state
from tests.support import (
    make_data_root,
    remote_repo_payload,
    selection_payload,
    state_payload,
    write_identity_file,
    write_manager_config,
    write_remote_repo_config,
    write_state_file,
)


def test_render_outputs_preview_only_without_writing_files(tmp_path: Path) -> None:
    data_root = make_data_root(tmp_path)
    config_path = write_manager_config(data_root / "config.json")
    config = load_manager_config(config_path, data_root=data_root)
    repo_root = data_root / "repos" / "keys"
    write_identity_file(repo_root)
    write_remote_repo_config(
        repo_root,
        payload=remote_repo_payload(endpoint_name="public", auth_name="home"),
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

    result = render_selected_state(config)

    assert "Host demo" in result.content
    assert not config.managed_config_path.exists()
    assert not (config.managed_keys_dir / "demo" / "id_demo").exists()
    assert result.planned_key_copies[0].target == config.managed_keys_dir / "demo" / "id_demo"


def test_render_is_stable_when_remote_option_order_changes(tmp_path: Path) -> None:
    data_root = make_data_root(tmp_path)
    config_path = write_manager_config(data_root / "config.json")
    config = load_manager_config(config_path, data_root=data_root)
    repo_root = data_root / "repos" / "keys"
    write_identity_file(repo_root, "keys/id_home")
    write_identity_file(repo_root, "keys/id_work")
    write_state_file(
        config.state_path,
        payload=state_payload(
            selected_hosts=[
                selection_payload(
                    server_name="demo",
                    endpoint_name="private",
                    authentication_name="work",
                )
            ]
        ),
    )

    first_payload = remote_repo_payload(
        endpoints=[
            {"EndPointName": "public", "HostName": "public.example.com", "Port": 22},
            {"EndPointName": "private", "HostName": "private.example.com", "Port": 2200},
        ],
        authentications=[
            {
                "AuthenticationName": "home",
                "User": "fox",
                "IdentityFile": "keys/id_home",
            },
            {
                "AuthenticationName": "work",
                "User": "ops",
                "IdentityFile": "keys/id_work",
            },
        ],
    )
    second_payload = remote_repo_payload(
        endpoints=list(reversed(first_payload[0]["Endpoint"])),
        authentications=list(reversed(first_payload[0]["Authentication"])),
    )

    write_remote_repo_config(repo_root, payload=first_payload)
    first_render = render_selected_state(config)

    write_remote_repo_config(repo_root, payload=second_payload)
    second_render = render_selected_state(config)

    assert "HostName private.example.com" in first_render.content
    assert "User ops" in first_render.content
    assert first_render.content == second_render.content
