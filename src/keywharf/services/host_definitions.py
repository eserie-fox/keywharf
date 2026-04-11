"""Services for loading, validating, and resolving host definitions from the host repo."""

from __future__ import annotations

from typing import Protocol

from keywharf.config.resolver import ResolvedManagerConfig
from keywharf.domain.errors import KeywharfError
from keywharf.domain.models import (
    HostAuthenticationOption,
    HostDefinition,
    HostEndpointOption,
    SelectedHostState,
    SSHHostConfig,
)
from keywharf.domain.results import ResolvedHostSelection, ValidationResult
from keywharf.ssh_config.builder import SSHHostConfigChoice, build_host_config
from keywharf.storage.host_repo import load_host_repo_entries


class _NamedHostOption(Protocol):
    name: str | None


def load_host_definition_list(config: ResolvedManagerConfig) -> list[HostDefinition]:
    return [HostDefinition.from_dict(item) for item in load_host_repo_entries(config)]


def load_host_definition_map(config: ResolvedManagerConfig) -> dict[str, HostDefinition]:
    mapping: dict[str, HostDefinition] = {}
    for host_definition in load_host_definition_list(config):
        if not host_definition.server_name:
            continue
        if host_definition.server_name in mapping:
            raise KeywharfError(
                f"Host repo config contains duplicate ServerName '{host_definition.server_name}'."
            )
        mapping[host_definition.server_name] = host_definition
    return mapping


def validate_host_repo_structure(
    config: ResolvedManagerConfig,
    host_definitions: list[HostDefinition],
    *,
    allow_empty: bool = False,
) -> ValidationResult:
    errors: list[str] = []
    if not host_definitions and not allow_empty:
        errors.append("Host repo config is empty.")

    seen_server_names: set[str] = set()
    for host_definition in host_definitions:
        server_name = host_definition.server_name
        if not server_name:
            errors.append("Host repo entry is missing ServerName.")
            continue
        if server_name in seen_server_names:
            errors.append(f"Duplicate ServerName '{server_name}' in host repo config.")
        else:
            seen_server_names.add(server_name)

        errors.extend(
            _validate_named_options(
                server_name,
                host_definition.endpoints,
                label="Endpoint",
                field_name="EndPointName",
            )
        )
        errors.extend(
            _validate_named_options(
                server_name,
                host_definition.authentication,
                label="Authentication",
                field_name="AuthenticationName",
            )
        )

        for endpoint in host_definition.endpoints:
            if endpoint.hostname is None:
                errors.append(f"Endpoint for '{server_name}' is missing HostName.")

        for auth in host_definition.authentication:
            if auth.user is None and auth.identity_file is None:
                errors.append(
                    f"Authentication for '{server_name}' must set User or IdentityFile."
                )
            if not auth.identity_file:
                continue
            identity_path = config.resolve_from_host_repo(auth.identity_file)
            if not identity_path.exists():
                errors.append(f"Identity file {identity_path.as_posix()} not found")

    return ValidationResult(ok=not errors, errors=errors)


def collect_incomplete_host_errors(host_definitions: list[HostDefinition]) -> tuple[list[str], set[str]]:
    errors: list[str] = []
    incomplete_hosts: set[str] = set()
    for host_definition in host_definitions:
        server_name = host_definition.server_name
        if not server_name:
            continue
        issue = _incomplete_host_error(server_name, host_definition)
        if issue is None:
            continue
        errors.append(issue)
        incomplete_hosts.add(server_name)
    return errors, incomplete_hosts


def incomplete_host_guidance() -> str:
    return (
        "Add missing options with "
        "'keywharf repo host endpoint add <server_name> <endpoint_name> --hostname <host>' "
        "and 'keywharf repo host auth add <server_name> <auth_name> "
        "[--user <user>] [--identity-file <path>]'."
    )


def resolve_selection(
    host_definitions: dict[str, HostDefinition],
    selection: SelectedHostState,
) -> ResolvedHostSelection:
    selection_errors = validate_selection(host_definitions, selection)
    if selection_errors:
        raise KeywharfError("\n".join(selection_errors))

    host_definition = host_definitions.get(selection.server_name)
    if host_definition is None:
        raise KeywharfError(
            f"Selected host '{selection.server_name}' is not present in the host repo."
        )

    endpoint_index, endpoint = _resolve_named_option(
        host_definition.endpoints,
        requested_name=selection.endpoint_name,
        label="endpoint",
        field_name="EndPointName",
        server_name=selection.server_name,
    )
    auth_index, authentication = _resolve_named_option(
        host_definition.authentication,
        requested_name=selection.authentication_name,
        label="authentication",
        field_name="AuthenticationName",
        server_name=selection.server_name,
    )
    return ResolvedHostSelection(
        selection=selection,
        host_definition=host_definition,
        endpoint=endpoint,
        authentication=authentication,
        endpoint_index=endpoint_index,
        authentication_index=auth_index,
    )


def validate_selection(
    host_definitions: dict[str, HostDefinition],
    selection: SelectedHostState,
) -> list[str]:
    host_definition = host_definitions.get(selection.server_name)
    if host_definition is None:
        return [f"Selected host '{selection.server_name}' is not present in the host repo."]

    completeness_error = _selection_incomplete_host_errors(
        selection.server_name,
        host_definition,
    )
    if completeness_error:
        return completeness_error

    errors: list[str] = []
    errors.extend(
        _validate_requested_option(
            host_definition.endpoints,
            requested_name=selection.endpoint_name,
            label="endpoint",
            field_name="EndPointName",
            server_name=selection.server_name,
        )
    )
    errors.extend(
        _validate_requested_option(
            host_definition.authentication,
            requested_name=selection.authentication_name,
            label="authentication",
            field_name="AuthenticationName",
            server_name=selection.server_name,
        )
    )
    return errors


def build_host_config_by_name(
    config: ResolvedManagerConfig,
    host_definitions: dict[str, HostDefinition],
    *,
    server_name: str,
    endpoint_id: int = 0,
    auth_id: int = 0,
) -> SSHHostConfig:
    host_definition = host_definitions.get(server_name)
    if host_definition is None:
        raise KeywharfError(f"Unknown host name: {server_name}")
    return build_host_config(
        SSHHostConfigChoice(
            manager_config=config,
            host_definition=host_definition,
            endpoint_id=endpoint_id,
            auth_id=auth_id,
        )
    )


def build_host_config_from_selection(
    config: ResolvedManagerConfig,
    host_definitions: dict[str, HostDefinition],
    selection: SelectedHostState,
) -> tuple[ResolvedHostSelection, SSHHostConfig]:
    resolved = resolve_selection(host_definitions, selection)
    host_config = build_host_config(
        SSHHostConfigChoice(
            manager_config=config,
            host_definition=resolved.host_definition,
            endpoint_id=resolved.endpoint_index,
            auth_id=resolved.authentication_index,
        )
    )
    return resolved, host_config


def _validate_named_options(
    server_name: str,
    options: list[_NamedHostOption],
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
            errors.append(f"Config '{server_name}' has duplicate {field_name} '{option.name}'.")
            continue
        seen_names.add(option.name)
    return errors


def _resolve_named_option(
    options: list[HostEndpointOption] | list[HostAuthenticationOption],
    *,
    requested_name: str | None,
    label: str,
    field_name: str,
    server_name: str,
) -> tuple[int, HostEndpointOption | HostAuthenticationOption]:
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
        raise KeywharfError(f"Config '{server_name}' has no {label} named '{requested_name}'.")
    index, option = matches[0]
    return index, option


def _validate_requested_option(
    options: list[HostEndpointOption] | list[HostAuthenticationOption],
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
    return [f"Config '{server_name}' has no {label} named '{requested_name}'."]


def _incomplete_host_error(
    server_name: str,
    host_definition: HostDefinition,
) -> str | None:
    missing_endpoint = not host_definition.endpoints
    missing_auth = not host_definition.authentication
    if missing_endpoint and missing_auth:
        return f"Host '{server_name}' has no endpoint or authentication options."
    if missing_endpoint:
        return f"Host '{server_name}' has no endpoint options."
    if missing_auth:
        return f"Host '{server_name}' has no authentication options."
    return None


def _selection_incomplete_host_errors(
    server_name: str,
    host_definition: HostDefinition,
) -> list[str]:
    missing_endpoint = not host_definition.endpoints
    missing_auth = not host_definition.authentication
    if not missing_endpoint and not missing_auth:
        return []

    errors = [_incomplete_host_error(server_name, host_definition) or ""]
    if missing_endpoint:
        errors.append(
            f"Run 'keywharf repo host endpoint add {server_name} <endpoint_name> --hostname <host>'."
        )
    if missing_auth:
        errors.append(
            f"Run 'keywharf repo host auth add {server_name} <auth_name> [--user <user>] [--identity-file <path>]'."
        )
    return errors
