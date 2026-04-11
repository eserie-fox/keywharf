from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from keywharf.config.loader import load_resolved_manager_config


def write_json(path: Path, payload: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def make_workspace(base: Path, *, marker_name: str = "KEYWHARF_WORKSPACE") -> Path:
    workspace_root = base / "workspace"
    workspace_root.mkdir(parents=True, exist_ok=True)
    (workspace_root / marker_name).write_text("", encoding="utf-8")
    return workspace_root


def manager_config_payload(
    *,
    host_repo_remote_url: str | None = None,
    host_repo_path: str | None = None,
    ssh_dir: str = "%{WORKSPACE}/ssh-home",
    managed_config_path: str | None = None,
    managed_keys_dir: str | None = None,
    state_path: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "host_repo_remote_url": host_repo_remote_url,
        "ssh_dir": ssh_dir,
    }
    if host_repo_path is not None:
        payload["host_repo_path"] = host_repo_path
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
    host_repo_remote_url: str | None = None,
    host_repo_path: str | None = None,
    ssh_dir: str = "%{WORKSPACE}/ssh-home",
    managed_config_path: str | None = None,
    managed_keys_dir: str | None = None,
    state_path: str | None = None,
) -> Path:
    return write_json(
        config_path,
        manager_config_payload(
            host_repo_remote_url=host_repo_remote_url,
            host_repo_path=host_repo_path,
            ssh_dir=ssh_dir,
            managed_config_path=managed_config_path,
            managed_keys_dir=managed_keys_dir,
            state_path=state_path,
        ),
    )


def load_config(config_path: Path, *, workspace_root: Path | None = None):
    return load_resolved_manager_config(config_path, workspace_root=workspace_root)


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


def endpoint_payload(
    *,
    name: str | None = "public",
    hostname: str | None = "example.com",
    port: int | None = 22,
    comment: str | None = "public",
) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if name is not None:
        payload["EndPointName"] = name
    if hostname is not None:
        payload["HostName"] = hostname
    if port is not None:
        payload["Port"] = port
    if comment is not None:
        payload["Comment"] = comment
    return payload


def auth_payload(
    *,
    name: str | None = "home",
    user: str | None = "fox",
    identity_file: str | None = "keys/id_demo",
    comment: str | None = "main key",
) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if name is not None:
        payload["AuthenticationName"] = name
    if user is not None:
        payload["User"] = user
    if identity_file is not None:
        payload["IdentityFile"] = identity_file
    if comment is not None:
        payload["Comment"] = comment
    return payload


def host_shell_payload(
    *,
    server_name: str = "demo",
    comment: str | None = "demo host",
    extra_config: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"ServerName": server_name}
    if comment is not None:
        payload["Comment"] = comment
    if extra_config is not None:
        payload["ExtraConfig"] = extra_config
    else:
        payload["ExtraConfig"] = [
            {
                "Key": "ProxyJump",
                "Value": "bastion",
                "Comment": "optional hop",
            }
        ]
    return payload


def host_repo_payload(
    *,
    server_name: str = "demo",
    endpoint_name: str | None = None,
    auth_name: str | None = None,
    hostname: str = "example.com",
    port: int | None = 22,
    user: str | None = "fox",
    identity_file: str | None = "keys/id_demo",
    comment: str | None = "demo host",
    endpoint_comment: str | None = "public",
    auth_comment: str | None = "main key",
    endpoints: list[dict[str, Any]] | None = None,
    authentications: list[dict[str, Any]] | None = None,
    extra_config: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    payload = host_shell_payload(
        server_name=server_name,
        comment=comment,
        extra_config=extra_config,
    )
    payload["Endpoint"] = (
        endpoints
        if endpoints is not None
        else [
            endpoint_payload(
                name=endpoint_name,
                hostname=hostname,
                port=port,
                comment=endpoint_comment,
            )
        ]
    )
    payload["Authentication"] = (
        authentications
        if authentications is not None
        else [
            auth_payload(
                name=auth_name,
                user=user,
                identity_file=identity_file,
                comment=auth_comment,
            )
        ]
    )
    return [payload]


def write_host_repo_config(host_repo_path: Path, payload: list[dict[str, Any]] | None = None) -> Path:
    host_repo_path.mkdir(parents=True, exist_ok=True)
    return write_json(
        host_repo_path / "config.json",
        host_repo_payload() if payload is None else payload,
    )


def write_identity_file(
    host_repo_path: Path,
    relative_path: str = "keys/id_demo",
    content: str = "PRIVATE KEY",
) -> Path:
    path = host_repo_path / relative_path
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
