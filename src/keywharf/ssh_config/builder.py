"""Low-level host-config builders."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from keywharf.config.resolver import ResolvedManagerConfig
from keywharf.domain.errors import KeywharfError
from keywharf.domain.models import (
    HostDefinition,
    SSHAuthentication,
    SSHEndpoint,
    SSHExtraConfig,
    SSHHostConfig,
)
from keywharf.ssh_config.render import render_host_config, render_ssh_config


def get_identity_file_path(
    managed_keys_directory: str | Path, server_name: str, original_identifier_file_path: str
) -> str:
    keys_dir = Path(str(managed_keys_directory)).expanduser()
    return (keys_dir / server_name / Path(original_identifier_file_path).name).as_posix()


@dataclass(slots=True)
class SSHHostConfigChoice:
    manager_config: ResolvedManagerConfig
    host_definition: HostDefinition
    endpoint_id: int = 0
    auth_id: int = 0


def build_host_config(choice: SSHHostConfigChoice) -> SSHHostConfig:
    host = choice.host_definition
    if not host.server_name:
        raise KeywharfError("Host definition is missing ServerName")
    if not host.endpoints:
        raise KeywharfError(f"Config '{host.server_name}' has no endpoint options.")
    if not host.authentication:
        raise KeywharfError(f"Config '{host.server_name}' has no authentication options.")
    if choice.endpoint_id < 0 or choice.endpoint_id >= len(host.endpoints):
        raise KeywharfError(
            f"Endpoint index out of range for '{host.server_name}'. Valid range: 0-{len(host.endpoints) - 1}."
        )
    if choice.auth_id < 0 or choice.auth_id >= len(host.authentication):
        raise KeywharfError(
            f"Authentication index out of range for '{host.server_name}'. Valid range: 0-{len(host.authentication) - 1}."
        )

    endpoint = host.endpoints[choice.endpoint_id]
    auth = host.authentication[choice.auth_id]

    identity_target = None
    identity_source = None
    if auth.identity_file:
        identity_source = choice.manager_config.resolve_from_host_repo(auth.identity_file).as_posix()
        identity_target = get_identity_file_path(
            choice.manager_config.managed_keys_dir,
            host.server_name,
            auth.identity_file,
        )

    return SSHHostConfig(
        name=host.server_name,
        comment=host.comment,
        endpoint=SSHEndpoint(
            hostname=endpoint.hostname,
            port=endpoint.port,
            comment=endpoint.comment,
        ),
        authentication=SSHAuthentication(
            user=auth.user,
            identity_file=identity_target,
            source_identity_file=identity_source,
            comment=auth.comment,
        ),
        extra_config=[
            SSHExtraConfig(key=item.key, value=item.value, comment=item.comment)
            for item in host.extra_config
        ],
    )


__all__ = [
    "SSHAuthentication",
    "SSHEndpoint",
    "SSHExtraConfig",
    "SSHHostConfig",
    "SSHHostConfigChoice",
    "build_host_config",
    "get_identity_file_path",
    "render_host_config",
    "render_ssh_config",
]
