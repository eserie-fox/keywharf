"""Structured editing of host-level fields in the host repo."""

from __future__ import annotations

from keywharf.config.resolver import ResolvedManagerConfig
from keywharf.domain.errors import KeywharfError
from keywharf.domain.models import HostDefinition, validate_name_list, validate_ssh_name
from keywharf.domain.results import HostRepoMutationResult
from keywharf.services.host_repo_editor_common import (
    build_selection_warnings,
    clean_optional_setter,
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
    aliases: list[str] | None = None,
) -> HostRepoMutationResult:
    host_definitions = load_host_definitions_or_raise(config)
    try:
        clean_server_name = validate_ssh_name(server_name)
        validate_name_list([] if aliases is None else aliases, label="Aliases")
    except ValueError as exc:
        raise KeywharfError(str(exc)) from exc
    ensure_unique_host_name(host_definitions, clean_server_name)

    try:
        new_host = HostDefinition(
            server_name=clean_server_name,
            aliases=[] if aliases is None else aliases,
            comment=clean_optional_setter(comment, label="comment"),
        )
    except ValueError as exc:
        raise KeywharfError(str(exc)) from exc
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
    aliases: list[str] | None = None,
    clear_comment: bool = False,
    clear_aliases: bool = False,
) -> HostRepoMutationResult:
    host_definitions = load_host_definitions_or_raise(config)
    index, current = find_host_index(host_definitions, server_name)
    updated = copy_host_definition(current)

    if aliases is not None and clear_aliases:
        raise KeywharfError("--alias cannot be used with --clear-aliases.")
    if clear_aliases:
        updated.aliases = []
    elif aliases is not None:
        updated.aliases = aliases
    if new_name is not None:
        try:
            updated.server_name = validate_ssh_name(new_name)
        except ValueError as exc:
            raise KeywharfError(str(exc)) from exc
        ensure_unique_host_name(host_definitions, updated.server_name, ignore_index=index)
    if clear_comment:
        updated.comment = None
    elif comment is not None:
        updated.comment = clean_optional_setter(comment, label="comment")

    try:
        updated.validate_names()
    except ValueError as exc:
        raise KeywharfError(str(exc)) from exc
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
            removed_aliases=[name for name in current.aliases if name not in updated.aliases],
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
