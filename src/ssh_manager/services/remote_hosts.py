"""Services for loading and building remote host definitions."""

from __future__ import annotations

from pathlib import Path

from ssh_manager.domain.errors import SSHManagerError
from ssh_manager.domain.models import ManagerConfig, RemoteHostDefinition, SSHHostConfig
from ssh_manager.ssh_config.builder import SSHHostConfigChoice, build_host_config
from ssh_manager.storage.json_store import read_json_list


REMOTE_CONFIG_FILENAME = "config.json"


def remote_config_path(config: ManagerConfig) -> Path:
    return config.ssh_key_local_repo / REMOTE_CONFIG_FILENAME


def load_remote_host_list(config: ManagerConfig) -> list[RemoteHostDefinition]:
    return [
        RemoteHostDefinition.from_dict(item)
        for item in read_json_list(remote_config_path(config))
    ]


def load_remote_host_map(config: ManagerConfig) -> dict[str, RemoteHostDefinition]:
    mapping: dict[str, RemoteHostDefinition] = {}
    for host in load_remote_host_list(config):
        if host.server_name:
            mapping[host.server_name] = host
    return mapping


def remote_host_map_to_dict(
    remote_hosts: dict[str, RemoteHostDefinition],
) -> dict[str, dict[str, object]]:
    return {name: host.to_dict() for name, host in remote_hosts.items()}


def build_remote_host_config(
    config: ManagerConfig,
    remote_hosts: dict[str, RemoteHostDefinition],
    *,
    server_name: str,
    endpoint_id: int = 0,
    auth_id: int = 0,
) -> SSHHostConfig:
    remote_host = remote_hosts.get(server_name)
    if remote_host is None:
        raise SSHManagerError(f"Unknown server name: {server_name}")
    return build_host_config(
        SSHHostConfigChoice(
            manager_config=config,
            remote_host=remote_host,
            endpoint_id=endpoint_id,
            auth_id=auth_id,
        )
    )
