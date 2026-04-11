"""Structured editing of authentication options in the host repo."""

from __future__ import annotations

from keywharf.config.resolver import ResolvedManagerConfig
from keywharf.domain.errors import KeywharfError
from keywharf.domain.models import HostAuthenticationOption
from keywharf.domain.results import HostRepoMutationResult
from keywharf.services.host_repo_editor_common import (
    build_selection_warnings,
    clean_optional_setter,
    clean_required_text,
    copy_host_definition,
    ensure_unique_auth_name,
    find_auth_index,
    find_host_index,
    load_host_definitions_or_raise,
    persist_host_definitions,
)
from keywharf.storage.host_repo import host_repo_config_path


def list_auth_options(config: ResolvedManagerConfig, server_name: str) -> list[HostAuthenticationOption]:
    _, host_definition = find_host_index(load_host_definitions_or_raise(config), server_name)
    return host_definition.authentication


def get_auth_option(
    config: ResolvedManagerConfig,
    *,
    server_name: str,
    auth_name: str,
) -> HostAuthenticationOption:
    _, host_definition = find_host_index(load_host_definitions_or_raise(config), server_name)
    _, auth = find_auth_index(host_definition, auth_name)
    return auth


def add_auth_option(
    config: ResolvedManagerConfig,
    *,
    server_name: str,
    auth_name: str,
    user: str | None = None,
    identity_file: str | None = None,
    comment: str | None = None,
) -> HostRepoMutationResult:
    host_definitions = load_host_definitions_or_raise(config)
    host_index, current = find_host_index(host_definitions, server_name)
    updated = copy_host_definition(current)

    clean_auth_name = clean_required_text(auth_name, label="authentication name")
    ensure_unique_auth_name(updated, clean_auth_name)
    clean_user = clean_optional_setter(user, label="user")
    clean_identity_file = clean_optional_setter(identity_file, label="identity file")
    if clean_user is None and clean_identity_file is None:
        raise KeywharfError(
            f"Authentication '{clean_auth_name}' for host '{server_name}' must set user or identity file."
        )

    auth = HostAuthenticationOption(
        name=clean_auth_name,
        user=clean_user,
        identity_file=clean_identity_file,
        comment=clean_optional_setter(comment, label="comment"),
    )
    updated.authentication.append(auth)

    host_definitions[host_index] = updated
    persist_host_definitions(config, host_definitions)
    return HostRepoMutationResult(
        operation="add",
        subject="auth",
        config_path=host_repo_config_path(config),
        name=clean_auth_name,
        server_name=server_name,
        host=updated,
        auth=auth,
    )


def update_auth_option(
    config: ResolvedManagerConfig,
    *,
    server_name: str,
    auth_name: str,
    new_name: str | None = None,
    user: str | None = None,
    clear_user: bool = False,
    identity_file: str | None = None,
    clear_identity_file: bool = False,
    comment: str | None = None,
    clear_comment: bool = False,
) -> HostRepoMutationResult:
    host_definitions = load_host_definitions_or_raise(config)
    host_index, current = find_host_index(host_definitions, server_name)
    updated = copy_host_definition(current)
    auth_index, auth = find_auth_index(updated, auth_name)
    original_name = auth.name or auth_name

    if new_name is not None:
        auth.name = clean_required_text(new_name, label="new authentication name")
        ensure_unique_auth_name(updated, auth.name, ignore_index=auth_index)
    if clear_user:
        auth.user = None
    elif user is not None:
        auth.user = clean_optional_setter(user, label="user")
    if clear_identity_file:
        auth.identity_file = None
    elif identity_file is not None:
        auth.identity_file = clean_optional_setter(identity_file, label="identity file")
    if clear_comment:
        auth.comment = None
    elif comment is not None:
        auth.comment = clean_optional_setter(comment, label="comment")

    if auth.user is None and auth.identity_file is None:
        raise KeywharfError(
            f"Authentication '{original_name}' for host '{server_name}' must set user or identity file."
        )

    if updated.to_dict() == current.to_dict():
        return HostRepoMutationResult(
            operation="update",
            subject="auth",
            config_path=host_repo_config_path(config),
            name=original_name,
            server_name=server_name,
            host=current,
            auth=current.authentication[auth_index],
            changed=False,
        )

    host_definitions[host_index] = updated
    persist_host_definitions(config, host_definitions)
    updated_auth = updated.authentication[auth_index]
    return HostRepoMutationResult(
        operation="update",
        subject="auth",
        config_path=host_repo_config_path(config),
        name=updated_auth.name or original_name,
        server_name=server_name,
        host=updated,
        auth=updated_auth,
        warnings=build_selection_warnings(
            config,
            old_server_name=server_name,
            old_auth_name=original_name,
            new_auth_name=updated_auth.name,
        ),
    )


def remove_auth_option(
    config: ResolvedManagerConfig,
    *,
    server_name: str,
    auth_name: str,
) -> HostRepoMutationResult:
    host_definitions = load_host_definitions_or_raise(config)
    host_index, current = find_host_index(host_definitions, server_name)
    updated = copy_host_definition(current)
    auth_index, auth = find_auth_index(updated, auth_name)
    del updated.authentication[auth_index]

    host_definitions[host_index] = updated
    persist_host_definitions(config, host_definitions)
    return HostRepoMutationResult(
        operation="remove",
        subject="auth",
        config_path=host_repo_config_path(config),
        name=auth_name,
        server_name=server_name,
        host=updated,
        auth=auth,
        warnings=build_selection_warnings(
            config,
            old_server_name=server_name,
            removed_auth_name=auth_name,
        ),
    )
