"""Shared helpers for structured host-repo editing."""

from __future__ import annotations

from collections.abc import Sequence
from copy import deepcopy
from typing import TypeVar

from keywharf.config.resolver import ResolvedManagerConfig
from keywharf.domain.errors import KeywharfError
from keywharf.domain.models import (
    HostAuthenticationOption,
    HostDefinition,
    HostEndpointOption,
)
from keywharf.services.host_definitions import (
    load_host_definition_list,
    validate_host_repo_structure,
)
from keywharf.services.host_repo_setup import missing_host_repo_config_message
from keywharf.services.privilege import can_read_path, can_write_file, root_owned_hint
from keywharf.storage.host_repo import host_repo_config_path, write_host_repo_entries
from keywharf.storage.state_store import load_state

OptionT = TypeVar("OptionT", HostEndpointOption, HostAuthenticationOption)


def analyze_host_repo_config_write_root_requirements(
    config: ResolvedManagerConfig,
) -> list[str]:
    """Return concrete privilege reasons for mutating the host repo config."""

    config_path = host_repo_config_path(config)
    reasons: list[str] = []
    if config_path.exists() and not can_read_path(config_path):
        hint = root_owned_hint(config_path)
        reasons.append(f"host repo config is not readable by current user: {config_path}{hint}")
    if not can_write_file(config_path):
        hint = root_owned_hint(config_path.parent)
        reasons.append(
            f"host repo config path is not writable by current user: {config_path}{hint}"
        )
    return reasons


def load_host_definitions_or_raise(
    config: ResolvedManagerConfig,
) -> list[HostDefinition]:
    try:
        return load_host_definition_list(config)
    except FileNotFoundError as exc:
        raise KeywharfError(missing_host_repo_config_message(config), exit_code=2) from exc


def persist_host_definitions(
    config: ResolvedManagerConfig,
    host_definitions: list[HostDefinition],
) -> None:
    validation = validate_host_repo_structure(config, host_definitions, allow_empty=True)
    if validation.errors:
        raise KeywharfError("\n".join(validation.errors))
    write_host_repo_entries(config, [host.to_dict() for host in host_definitions])


def find_host_index(
    host_definitions: Sequence[HostDefinition],
    server_name: str,
) -> tuple[int, HostDefinition]:
    for index, host_definition in enumerate(host_definitions):
        if host_definition.server_name == server_name:
            return index, host_definition
    raise KeywharfError(f"Host '{server_name}' not found in the host repo.")


def copy_host_definition(host_definition: HostDefinition) -> HostDefinition:
    return deepcopy(host_definition)


def ensure_unique_host_name(
    host_definitions: Sequence[HostDefinition],
    server_name: str,
    *,
    ignore_index: int | None = None,
) -> None:
    for index, host_definition in enumerate(host_definitions):
        if ignore_index is not None and index == ignore_index:
            continue
        if host_definition.server_name == server_name:
            raise KeywharfError(f"Host '{server_name}' already exists in the host repo.")


def find_endpoint_index(
    host_definition: HostDefinition,
    endpoint_name: str,
) -> tuple[int, HostEndpointOption]:
    return _find_named_option_index(
        host_definition.endpoints,
        option_name=endpoint_name,
        server_name=host_definition.server_name or "host",
        label="endpoint",
    )


def find_auth_index(
    host_definition: HostDefinition,
    auth_name: str,
) -> tuple[int, HostAuthenticationOption]:
    return _find_named_option_index(
        host_definition.authentication,
        option_name=auth_name,
        server_name=host_definition.server_name or "host",
        label="authentication",
    )


def ensure_unique_endpoint_name(
    host_definition: HostDefinition,
    endpoint_name: str,
    *,
    ignore_index: int | None = None,
) -> None:
    _ensure_unique_named_option(
        host_definition.endpoints,
        option_name=endpoint_name,
        server_name=host_definition.server_name or "host",
        label="endpoint",
        ignore_index=ignore_index,
    )


def ensure_unique_auth_name(
    host_definition: HostDefinition,
    auth_name: str,
    *,
    ignore_index: int | None = None,
) -> None:
    _ensure_unique_named_option(
        host_definition.authentication,
        option_name=auth_name,
        server_name=host_definition.server_name or "host",
        label="authentication",
        ignore_index=ignore_index,
    )


def clean_required_text(value: str, *, label: str) -> str:
    text = value.strip()
    if not text:
        raise KeywharfError(f"{label} must not be blank.")
    return text


def clean_optional_setter(value: str | None, *, label: str) -> str | None:
    if value is None:
        return None
    text = value.strip()
    if not text:
        raise KeywharfError(f"{label} must not be blank.")
    return text


def build_selection_warnings(
    config: ResolvedManagerConfig,
    *,
    old_server_name: str | None = None,
    new_server_name: str | None = None,
    removed_server_name: str | None = None,
    old_endpoint_name: str | None = None,
    new_endpoint_name: str | None = None,
    removed_endpoint_name: str | None = None,
    old_auth_name: str | None = None,
    new_auth_name: str | None = None,
    removed_auth_name: str | None = None,
) -> list[str]:
    try:
        state = load_state(config)
    except Exception:
        return []

    warnings: list[str] = []
    target_server_name = old_server_name or new_server_name

    for selection in state.selected_hosts:
        if removed_server_name is not None and selection.server_name == removed_server_name:
            warnings.append(
                f"Local state still selects '{removed_server_name}'. Run "
                "'keywharf validate' and update the selection."
            )
        if (
            old_server_name is not None
            and new_server_name is not None
            and old_server_name != new_server_name
            and selection.server_name == old_server_name
        ):
            warnings.append(
                f"Local state still refers to host '{old_server_name}'. Run "
                "'keywharf validate' and update the selection."
            )
        if (
            target_server_name is not None
            and removed_endpoint_name is not None
            and selection.server_name == target_server_name
            and selection.endpoint_name == removed_endpoint_name
        ):
            warnings.append(
                f"Local state still refers to endpoint '{removed_endpoint_name}' for "
                f"'{target_server_name}'. Run 'keywharf validate' and update the selection."
            )
        if (
            target_server_name is not None
            and old_endpoint_name is not None
            and new_endpoint_name is not None
            and old_endpoint_name != new_endpoint_name
            and selection.server_name == target_server_name
            and selection.endpoint_name == old_endpoint_name
        ):
            warnings.append(
                f"Local state still refers to endpoint '{old_endpoint_name}' for "
                f"'{target_server_name}'. Run 'keywharf validate' and update the selection."
            )
        if (
            target_server_name is not None
            and removed_auth_name is not None
            and selection.server_name == target_server_name
            and selection.authentication_name == removed_auth_name
        ):
            warnings.append(
                f"Local state still refers to authentication '{removed_auth_name}' for "
                f"'{target_server_name}'. Run 'keywharf validate' and update the selection."
            )
        if (
            target_server_name is not None
            and old_auth_name is not None
            and new_auth_name is not None
            and old_auth_name != new_auth_name
            and selection.server_name == target_server_name
            and selection.authentication_name == old_auth_name
        ):
            warnings.append(
                f"Local state still refers to authentication '{old_auth_name}' for "
                f"'{target_server_name}'. Run 'keywharf validate' and update the selection."
            )

    return list(dict.fromkeys(warnings))


def _find_named_option_index(
    options: Sequence[OptionT],
    *,
    option_name: str,
    server_name: str,
    label: str,
) -> tuple[int, OptionT]:
    if not options:
        raise KeywharfError(f"Host '{server_name}' has no {label} options.")
    for index, option in enumerate(options):
        if option.name == option_name:
            return index, option
    raise KeywharfError(f"Host '{server_name}' has no {label} named '{option_name}'.")


def _ensure_unique_named_option(
    options: Sequence[OptionT],
    *,
    option_name: str,
    server_name: str,
    label: str,
    ignore_index: int | None = None,
) -> None:
    for index, option in enumerate(options):
        if ignore_index is not None and index == ignore_index:
            continue
        if option.name == option_name:
            raise KeywharfError(f"Host '{server_name}' already has {label} '{option_name}'.")
