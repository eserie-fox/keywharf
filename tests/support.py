from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_json(path: Path, payload: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def make_data_root(base: Path, *, marker_name: str = "SSH_MANAGER_DATA_ROOT") -> Path:
    data_root = base / "data-root"
    data_root.mkdir(parents=True, exist_ok=True)
    (data_root / marker_name).write_text("", encoding="utf-8")
    return data_root


def manager_config_payload(
    *,
    ssh_key_remote_repo: str = "git@example.com:org/keys.git",
    ssh_key_local_repo: str = "%{DATA_ROOT}/repos/keys",
    ssh_dir: str = "%{DATA_ROOT}/ssh-home",
    managed_config_path: str | None = None,
    managed_keys_dir: str | None = None,
    state_path: str | None = None,
) -> dict[str, Any]:
    payload = {
        "ssh_key_remote_repo": ssh_key_remote_repo,
        "ssh_key_local_repo": ssh_key_local_repo,
        "ssh_dir": ssh_dir,
    }
    if managed_config_path is not None:
        payload["managed_config_path"] = managed_config_path
    if managed_keys_dir is not None:
        payload["managed_keys_dir"] = managed_keys_dir
    if state_path is not None:
        payload["state_path"] = state_path
    return payload


def write_manager_config(
    config_path: Path,
    *,
    ssh_key_remote_repo: str = "git@example.com:org/keys.git",
    ssh_key_local_repo: str = "%{DATA_ROOT}/repos/keys",
    ssh_dir: str = "%{DATA_ROOT}/ssh-home",
    managed_config_path: str | None = None,
    managed_keys_dir: str | None = None,
    state_path: str | None = None,
) -> Path:
    return write_json(
        config_path,
        manager_config_payload(
            ssh_key_remote_repo=ssh_key_remote_repo,
            ssh_key_local_repo=ssh_key_local_repo,
            ssh_dir=ssh_dir,
            managed_config_path=managed_config_path,
            managed_keys_dir=managed_keys_dir,
            state_path=state_path,
        ),
    )


def selection_payload(
    *,
    server_name: str = "demo",
    endpoint_name: str | None = None,
    authentication_name: str | None = None,
) -> dict[str, Any]:
    return {
        "server_name": server_name,
        "endpoint_name": endpoint_name,
        "authentication_name": authentication_name,
    }


def state_payload(
    *,
    selected_hosts: list[dict[str, Any]] | None = None,
    version: int = 1,
) -> dict[str, Any]:
    return {
        "version": version,
        "selected_hosts": selected_hosts or [],
    }


def write_state_file(path: Path, payload: dict[str, Any] | None = None) -> Path:
    return write_json(path, payload or state_payload())


def remote_repo_payload(
    *,
    server_name: str = "demo",
    endpoint_name: str | None = None,
    auth_name: str | None = None,
    hostname: str = "example.com",
    port: int = 22,
    user: str = "fox",
    identity_file: str = "keys/id_demo",
    endpoints: list[dict[str, Any]] | None = None,
    authentications: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    return [
        {
            "ServerName": server_name,
            "Comment": "demo host",
            "Endpoint": endpoints
            or [
                {
                    "EndPointName": endpoint_name,
                    "HostName": hostname,
                    "Port": port,
                    "Comment": "public",
                }
            ],
            "Authentication": authentications
            or [
                {
                    "AuthenticationName": auth_name,
                    "User": user,
                    "IdentityFile": identity_file,
                    "Comment": "main key",
                }
            ],
            "ExtraConfig": [
                {
                    "Key": "ProxyJump",
                    "Value": "bastion",
                    "Comment": "optional hop",
                }
            ],
        }
    ]


def write_remote_repo_config(repo_root: Path, payload: list[dict[str, Any]] | None = None) -> Path:
    repo_root.mkdir(parents=True, exist_ok=True)
    return write_json(repo_root / "config.json", payload or remote_repo_payload())


def write_identity_file(repo_root: Path, relative_path: str = "keys/id_demo", content: str = "PRIVATE KEY") -> Path:
    path = repo_root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def write_local_ssh_config(ssh_dir: Path, content: str) -> Path:
    ssh_dir.mkdir(parents=True, exist_ok=True)
    path = ssh_dir / "config"
    path.write_text(content, encoding="utf-8")
    return path


def write_managed_ssh_config(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path
