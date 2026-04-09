"""Higher-level host mutation operations."""

from __future__ import annotations

from ssh_manager.domain.errors import SSHManagerError
from ssh_manager.domain.models import ManagerConfig, RemoteHostDefinition, SSHHostConfig
from ssh_manager.domain.results import HostMutationResult
from ssh_manager.services.local_hosts import write_local_hosts
from ssh_manager.services.remote_hosts import build_remote_host_config
from ssh_manager.storage.ssh_files import copy_identity_file, delete_identity_file


def preview_add_host(
    config: ManagerConfig,
    remote_hosts: dict[str, RemoteHostDefinition],
    *,
    server_name: str,
    endpoint_id: int = 0,
    auth_id: int = 0,
) -> SSHHostConfig:
    return build_remote_host_config(
        config,
        remote_hosts,
        server_name=server_name,
        endpoint_id=endpoint_id,
        auth_id=auth_id,
    )


def add_host(
    config: ManagerConfig,
    current_hosts: list[SSHHostConfig],
    remote_hosts: dict[str, RemoteHostDefinition],
    *,
    server_name: str,
    endpoint_id: int = 0,
    auth_id: int = 0,
) -> HostMutationResult:
    if any(host.name == server_name for host in current_hosts):
        raise SSHManagerError(f"Config '{server_name}' already exists locally.")

    new_host = preview_add_host(
        config,
        remote_hosts,
        server_name=server_name,
        endpoint_id=endpoint_id,
        auth_id=auth_id,
    )
    source_identity = new_host.get_ssh_original_identity_file()
    target_identity = new_host.get_ssh_identity_file()
    copied_identity = False
    if source_identity and target_identity:
        copy_identity_file(source_identity, target_identity)
        copied_identity = True

    updated_hosts = sorted([*current_hosts, new_host], key=lambda host: host.name or "")
    try:
        write_local_hosts(config, updated_hosts, backup=True)
    except Exception:
        if copied_identity and target_identity:
            delete_identity_file(target_identity)
        raise
    return HostMutationResult(host=new_host, hosts=updated_hosts)


def resolve_local_host(
    current_hosts: list[SSHHostConfig], name_or_index: str
) -> tuple[int, SSHHostConfig]:
    for index, host in enumerate(current_hosts):
        if host.name == name_or_index:
            return index, host

    try:
        index = int(name_or_index)
    except ValueError as exc:
        raise SSHManagerError(
            f"No host named/indexed '{name_or_index}' found in ssh-manager managed config."
        ) from exc

    if index < 0 or index >= len(current_hosts):
        raise SSHManagerError(
            f"No host named/indexed '{name_or_index}' found in ssh-manager managed config."
        )
    return index, current_hosts[index]


def remove_host(
    config: ManagerConfig,
    current_hosts: list[SSHHostConfig],
    *,
    name_or_index: str,
) -> HostMutationResult:
    index, host = resolve_local_host(current_hosts, name_or_index)
    updated_hosts = [item for item_index, item in enumerate(current_hosts) if item_index != index]
    write_local_hosts(config, updated_hosts, backup=True)
    delete_identity_file(host.get_ssh_identity_file())
    return HostMutationResult(host=host, hosts=updated_hosts)


def flush_hosts(
    config: ManagerConfig,
    current_hosts: list[SSHHostConfig],
    *,
    backup: bool = True,
) -> None:
    write_local_hosts(config, current_hosts, backup=backup)
