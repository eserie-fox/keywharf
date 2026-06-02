"""Structured editing of host-level fields in the host repo."""

from __future__ import annotations

from keywharf.config.resolver import ResolvedManagerConfig
from keywharf.domain.models import HostDefinition
from keywharf.domain.results import HostRepoMutationResult
from keywharf.services.host_repo_editor_common import (
    build_selection_warnings,
    clean_optional_setter,
    clean_required_text,
    copy_host_definition,
    ensure_unique_host_name,
    find_host_index,
    load_host_definitions_or_raise,
    persist_host_definitions,
)
from keywharf.storage.host_repo import host_repo_config_path


def list_host_definitions(config: ResolvedManagerConfig) -> list[HostDefinition]:
    return load_host_definitions_or_raise(config)


def get_host_definition(config: ResolvedManagerConfig, server_name: str) -> HostDefinition:
    _, host_definition = find_host_index(load_host_definitions_or_raise(config), server_name)
    return host_definition


def add_host_definition(
    config: ResolvedManagerConfig,
    *,
    server_name: str,
    comment: str | None = None,
) -> HostRepoMutationResult:
    host_definitions = load_host_definitions_or_raise(config)
    clean_server_name = clean_required_text(server_name, label="server name")
    ensure_unique_host_name(host_definitions, clean_server_name)

    new_host = HostDefinition(
        server_name=clean_server_name,
        comment=clean_optional_setter(comment, label="comment"),
    )
    persist_host_definitions(config, [*host_definitions, new_host])
    return HostRepoMutationResult(
        operation="add",
        subject="host",
        config_path=host_repo_config_path(config),
        name=clean_server_name,
        host=new_host,
        notes=[
            f"Host '{clean_server_name}' has no endpoint or authentication options yet, "
            "so it cannot be selected.",
            f"Next: keywharf repo host endpoint add {clean_server_name} "
            "<endpoint_name> --hostname <host>",
            f"Next: keywharf repo host auth add {clean_server_name} <auth_name> "
            "[--user <user>] [--identity-file <path>]",
        ],
    )


def update_host_definition(
    config: ResolvedManagerConfig,
    *,
    server_name: str,
    new_name: str | None = None,
    comment: str | None = None,
    clear_comment: bool = False,
) -> HostRepoMutationResult:
    host_definitions = load_host_definitions_or_raise(config)
    index, current = find_host_index(host_definitions, server_name)
    updated = copy_host_definition(current)

    if new_name is not None:
        updated.server_name = clean_required_text(new_name, label="new server name")
        ensure_unique_host_name(host_definitions, updated.server_name, ignore_index=index)
    if clear_comment:
        updated.comment = None
    elif comment is not None:
        updated.comment = clean_optional_setter(comment, label="comment")

    if updated.to_dict() == current.to_dict():
        return HostRepoMutationResult(
            operation="update",
            subject="host",
            config_path=host_repo_config_path(config),
            name=current.server_name or server_name,
            host=current,
            changed=False,
        )

    host_definitions[index] = updated
    persist_host_definitions(config, host_definitions)
    return HostRepoMutationResult(
        operation="update",
        subject="host",
        config_path=host_repo_config_path(config),
        name=updated.server_name or server_name,
        host=updated,
        warnings=build_selection_warnings(
            config,
            old_server_name=current.server_name,
            new_server_name=updated.server_name,
        ),
    )


def remove_host_definition(
    config: ResolvedManagerConfig,
    *,
    server_name: str,
) -> HostRepoMutationResult:
    host_definitions = load_host_definitions_or_raise(config)
    index, removed = find_host_index(host_definitions, server_name)
    del host_definitions[index]
    persist_host_definitions(config, host_definitions)
    return HostRepoMutationResult(
        operation="remove",
        subject="host",
        config_path=host_repo_config_path(config),
        name=server_name,
        host=removed,
        warnings=build_selection_warnings(config, removed_server_name=server_name),
    )
