"""Structured editing of endpoint options in the host repo."""

from __future__ import annotations

from keywharf.config.resolver import ResolvedManagerConfig
from keywharf.domain.errors import KeywharfError
from keywharf.domain.models import HostEndpointOption
from keywharf.domain.results import HostRepoMutationResult
from keywharf.services.host_repo_editor_common import (
    build_selection_warnings,
    clean_optional_setter,
    clean_required_text,
    copy_host_definition,
    ensure_unique_endpoint_name,
    find_endpoint_index,
    find_host_index,
    load_host_definitions_or_raise,
    persist_host_definitions,
)
from keywharf.storage.host_repo import host_repo_config_path


def list_endpoints(config: ResolvedManagerConfig, server_name: str) -> list[HostEndpointOption]:
    _, host_definition = find_host_index(load_host_definitions_or_raise(config), server_name)
    return host_definition.endpoints


def get_endpoint(
    config: ResolvedManagerConfig,
    *,
    server_name: str,
    endpoint_name: str,
) -> HostEndpointOption:
    _, host_definition = find_host_index(load_host_definitions_or_raise(config), server_name)
    _, endpoint = find_endpoint_index(host_definition, endpoint_name)
    return endpoint


def add_endpoint(
    config: ResolvedManagerConfig,
    *,
    server_name: str,
    endpoint_name: str,
    hostname: str,
    port: int | None = None,
    comment: str | None = None,
) -> HostRepoMutationResult:
    host_definitions = load_host_definitions_or_raise(config)
    host_index, current = find_host_index(host_definitions, server_name)
    updated = copy_host_definition(current)

    clean_endpoint_name = clean_required_text(endpoint_name, label="endpoint name")
    ensure_unique_endpoint_name(updated, clean_endpoint_name)
    endpoint = HostEndpointOption(
        name=clean_endpoint_name,
        hostname=clean_required_text(hostname, label="hostname"),
        port=port,
        comment=clean_optional_setter(comment, label="comment"),
    )
    updated.endpoints.append(endpoint)

    host_definitions[host_index] = updated
    persist_host_definitions(config, host_definitions)
    return HostRepoMutationResult(
        operation="add",
        subject="endpoint",
        config_path=host_repo_config_path(config),
        name=clean_endpoint_name,
        server_name=server_name,
        host=updated,
        endpoint=endpoint,
    )


def update_endpoint(
    config: ResolvedManagerConfig,
    *,
    server_name: str,
    endpoint_name: str,
    new_name: str | None = None,
    hostname: str | None = None,
    port: int | None = None,
    clear_port: bool = False,
    comment: str | None = None,
    clear_comment: bool = False,
) -> HostRepoMutationResult:
    host_definitions = load_host_definitions_or_raise(config)
    host_index, current = find_host_index(host_definitions, server_name)
    updated = copy_host_definition(current)
    endpoint_index, endpoint = find_endpoint_index(updated, endpoint_name)
    original_name = endpoint.name or endpoint_name

    if new_name is not None:
        endpoint.name = clean_required_text(new_name, label="new endpoint name")
        ensure_unique_endpoint_name(updated, endpoint.name, ignore_index=endpoint_index)
    if hostname is not None:
        endpoint.hostname = clean_required_text(hostname, label="hostname")
    if clear_port:
        endpoint.port = None
    elif port is not None:
        endpoint.port = port
    if clear_comment:
        endpoint.comment = None
    elif comment is not None:
        endpoint.comment = clean_optional_setter(comment, label="comment")

    if endpoint.hostname is None:
        raise KeywharfError(
            f"Endpoint '{original_name}' for host '{server_name}' must set HostName."
        )

    if updated.to_dict() == current.to_dict():
        return HostRepoMutationResult(
            operation="update",
            subject="endpoint",
            config_path=host_repo_config_path(config),
            name=original_name,
            server_name=server_name,
            host=current,
            endpoint=current.endpoints[endpoint_index],
            changed=False,
        )

    host_definitions[host_index] = updated
    persist_host_definitions(config, host_definitions)
    updated_endpoint = updated.endpoints[endpoint_index]
    return HostRepoMutationResult(
        operation="update",
        subject="endpoint",
        config_path=host_repo_config_path(config),
        name=updated_endpoint.name or original_name,
        server_name=server_name,
        host=updated,
        endpoint=updated_endpoint,
        warnings=build_selection_warnings(
            config,
            old_server_name=server_name,
            old_endpoint_name=original_name,
            new_endpoint_name=updated_endpoint.name,
        ),
    )


def remove_endpoint(
    config: ResolvedManagerConfig,
    *,
    server_name: str,
    endpoint_name: str,
) -> HostRepoMutationResult:
    host_definitions = load_host_definitions_or_raise(config)
    host_index, current = find_host_index(host_definitions, server_name)
    updated = copy_host_definition(current)
    endpoint_index, endpoint = find_endpoint_index(updated, endpoint_name)
    del updated.endpoints[endpoint_index]

    host_definitions[host_index] = updated
    persist_host_definitions(config, host_definitions)
    return HostRepoMutationResult(
        operation="remove",
        subject="endpoint",
        config_path=host_repo_config_path(config),
        name=endpoint_name,
        server_name=server_name,
        host=updated,
        endpoint=endpoint,
        warnings=build_selection_warnings(
            config,
            old_server_name=server_name,
            removed_endpoint_name=endpoint_name,
        ),
    )
