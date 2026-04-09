"""Services for loading, validating, and resolving remote host definitions."""

from __future__ import annotations

from typing import Protocol

from keywharf.config.resolver import ResolvedManagerConfig
from keywharf.domain.errors import KeywharfError
from keywharf.domain.models import (
    RemoteAuthenticationOption,
    RemoteEndpointOption,
    RemoteHostDefinition,
    SSHHostConfig,
    SelectedHostState,
)
from keywharf.domain.results import ResolvedHostSelection, ValidationResult
from keywharf.ssh_config.builder import SSHHostConfigChoice, build_host_config
from keywharf.storage.remote_repo import load_remote_repo_entries


class _NamedRemoteOption(Protocol):
    name: str | None


def load_remote_host_list(config: ResolvedManagerConfig) -> list[RemoteHostDefinition]:
    return [
        RemoteHostDefinition.from_dict(item)
        for item in load_remote_repo_entries(config)
    ]


def load_remote_host_map(config: ResolvedManagerConfig) -> dict[str, RemoteHostDefinition]:
    mapping: dict[str, RemoteHostDefinition] = {}
    for host in load_remote_host_list(config):
        if not host.server_name:
            continue
        if host.server_name in mapping:
            raise KeywharfError(
                f"Remote repository config contains duplicate ServerName '{host.server_name}'."
            )
        mapping[host.server_name] = host
    return mapping


def remote_host_map_to_dict(
    remote_hosts: dict[str, RemoteHostDefinition],
) -> dict[str, dict[str, object]]:
    return {name: host.to_dict() for name, host in remote_hosts.items()}


def validate_remote_host_definitions(
    config: ResolvedManagerConfig,
    remote_hosts: list[RemoteHostDefinition],
) -> ValidationResult:
    errors: list[str] = []
    if not remote_hosts:
        errors.append("Remote repository config is empty.")

    seen_server_names: set[str] = set()
    for remote_host in remote_hosts:
        server_name = remote_host.server_name
        if not server_name:
            errors.append("Remote repository entry is missing ServerName.")
            continue
        if server_name in seen_server_names:
            errors.append(f"Duplicate ServerName '{server_name}' in remote repository config.")
        else:
            seen_server_names.add(server_name)

        if not remote_host.endpoints:
            errors.append(f"Config '{server_name}' has no endpoint options.")
        if not remote_host.authentication:
            errors.append(f"Config '{server_name}' has no authentication options.")

        errors.extend(
            _validate_named_options(
                server_name,
                remote_host.endpoints,
                label="Endpoint",
                field_name="EndPointName",
            )
        )
        errors.extend(
            _validate_named_options(
                server_name,
                remote_host.authentication,
                label="Authentication",
                field_name="AuthenticationName",
            )
        )

        for auth in remote_host.authentication:
            if not auth.identity_file:
                continue
            identity_path = config.resolve_from_local_repo(auth.identity_file)
            if not identity_path.exists():
                errors.append(f"Identity file {identity_path.as_posix()} not found")

    return ValidationResult(ok=not errors, errors=errors)


def resolve_selection(
    remote_hosts: dict[str, RemoteHostDefinition],
    selection: SelectedHostState,
) -> ResolvedHostSelection:
    selection_errors = validate_selection(remote_hosts, selection)
    if selection_errors:
        raise KeywharfError("\n".join(selection_errors))

    remote_host = remote_hosts.get(selection.server_name)
    if remote_host is None:
        raise KeywharfError(
            f"Selected host '{selection.server_name}' is not present in the remote repository."
        )

    endpoint_index, endpoint = _resolve_named_option(
        remote_host.endpoints,
        requested_name=selection.endpoint_name,
        label="endpoint",
        field_name="EndPointName",
        server_name=selection.server_name,
    )
    auth_index, authentication = _resolve_named_option(
        remote_host.authentication,
        requested_name=selection.authentication_name,
        label="authentication",
        field_name="AuthenticationName",
        server_name=selection.server_name,
    )
    return ResolvedHostSelection(
        selection=selection,
        remote_host=remote_host,
        endpoint=endpoint,
        authentication=authentication,
        endpoint_index=endpoint_index,
        authentication_index=auth_index,
    )


def validate_selection(
    remote_hosts: dict[str, RemoteHostDefinition],
    selection: SelectedHostState,
) -> list[str]:
    remote_host = remote_hosts.get(selection.server_name)
    if remote_host is None:
        return [
            f"Selected host '{selection.server_name}' is not present in the remote repository."
        ]

    errors: list[str] = []
    errors.extend(
        _validate_requested_option(
            remote_host.endpoints,
            requested_name=selection.endpoint_name,
            label="endpoint",
            field_name="EndPointName",
            server_name=selection.server_name,
        )
    )
    errors.extend(
        _validate_requested_option(
            remote_host.authentication,
            requested_name=selection.authentication_name,
            label="authentication",
            field_name="AuthenticationName",
            server_name=selection.server_name,
        )
    )
    return errors


def build_remote_host_config(
    config: ResolvedManagerConfig,
    remote_hosts: dict[str, RemoteHostDefinition],
    *,
    server_name: str,
    endpoint_id: int = 0,
    auth_id: int = 0,
) -> SSHHostConfig:
    remote_host = remote_hosts.get(server_name)
    if remote_host is None:
        raise KeywharfError(f"Unknown server name: {server_name}")
    return build_host_config(
        SSHHostConfigChoice(
            manager_config=config,
            remote_host=remote_host,
            endpoint_id=endpoint_id,
            auth_id=auth_id,
        )
    )


def build_remote_host_config_from_selection(
    config: ResolvedManagerConfig,
    remote_hosts: dict[str, RemoteHostDefinition],
    selection: SelectedHostState,
) -> tuple[ResolvedHostSelection, SSHHostConfig]:
    resolved = resolve_selection(remote_hosts, selection)
    host_config = build_host_config(
        SSHHostConfigChoice(
            manager_config=config,
            remote_host=resolved.remote_host,
            endpoint_id=resolved.endpoint_index,
            auth_id=resolved.authentication_index,
        )
    )
    return resolved, host_config


def _validate_named_options(
    server_name: str,
    options: list[_NamedRemoteOption],
    *,
    label: str,
    field_name: str,
) -> list[str]:
    errors: list[str] = []
    if len(options) <= 1:
        return errors

    seen_names: set[str] = set()
    for option in options:
        if option.name is None:
            errors.append(
                f"Config '{server_name}' has multiple {label.lower()} options; "
                f"each requires {field_name}."
            )
            continue
        if option.name in seen_names:
            errors.append(
                f"Config '{server_name}' has duplicate {field_name} '{option.name}'."
            )
            continue
        seen_names.add(option.name)
    return errors


def _resolve_named_option(
    options: list[RemoteEndpointOption] | list[RemoteAuthenticationOption],
    *,
    requested_name: str | None,
    label: str,
    field_name: str,
    server_name: str,
) -> tuple[int, RemoteEndpointOption | RemoteAuthenticationOption]:
    if not options:
        raise KeywharfError(f"Config '{server_name}' has no {label} options.")

    if requested_name is None:
        if len(options) == 1:
            return 0, options[0]
        raise KeywharfError(
            f"Config '{server_name}' has multiple {label} options. "
            f"Select one by stable name ({field_name})."
        )

    matches = [
        (index, option)
        for index, option in enumerate(options)
        if option.name == requested_name
    ]
    if not matches:
        raise KeywharfError(
            f"Config '{server_name}' has no {label} named '{requested_name}'."
        )
    index, option = matches[0]
    return index, option


def _validate_requested_option(
    options: list[RemoteEndpointOption] | list[RemoteAuthenticationOption],
    *,
    requested_name: str | None,
    label: str,
    field_name: str,
    server_name: str,
) -> list[str]:
    if not options:
        return [f"Config '{server_name}' has no {label} options."]

    if requested_name is None:
        if len(options) == 1:
            return []
        return [
            f"Config '{server_name}' has multiple {label} options. "
            f"Select one by stable name ({field_name})."
        ]

    if any(option.name == requested_name for option in options):
        return []
    return [
        f"Config '{server_name}' has no {label} named '{requested_name}'."
    ]
