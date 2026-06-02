"""State mutation services for selected hosts from the host repo."""

from __future__ import annotations

from keywharf.config.resolver import ResolvedManagerConfig
from keywharf.domain.errors import KeywharfError
from keywharf.domain.models import (
    HostDefinition,
    LocalState,
    SelectedHostState,
)
from keywharf.services.host_definitions import resolve_selection
from keywharf.services.privilege import can_read_path, can_write_file, root_owned_hint
from keywharf.storage.host_repo import host_repo_config_path
from keywharf.storage.state_store import load_state, save_state


def load_selected_state(config: ResolvedManagerConfig) -> LocalState:
    return load_state(config)


def select_host(
    config: ResolvedManagerConfig,
    host_definitions: dict[str, HostDefinition],
    *,
    server_name: str,
    endpoint_name: str | None = None,
    authentication_name: str | None = None,
) -> tuple[LocalState, SelectedHostState]:
    selection = SelectedHostState(
        server_name=server_name,
        endpoint_name=endpoint_name,
        authentication_name=authentication_name,
    )
    resolve_selection(host_definitions, selection)

    state = load_state(config)
    state.upsert(selection)
    save_state(config, state)
    return state, selection


def deselect_host(
    config: ResolvedManagerConfig,
    *,
    server_name: str,
) -> tuple[LocalState, SelectedHostState]:
    state = load_state(config)
    removed = state.remove(server_name)
    if removed is None:
        raise KeywharfError(f"Host '{server_name}' is not selected in local state.")
    save_state(config, state)
    return state, removed


def analyze_select_root_requirements(config: ResolvedManagerConfig) -> list[str]:
    """Return privilege reasons for mutating local state from host-repo data."""

    reasons: list[str] = []
    host_repo_config = host_repo_config_path(config)
    if host_repo_config.exists() and not can_read_path(host_repo_config):
        hint = root_owned_hint(host_repo_config)
        reasons.append(
            f"host repo config is not readable by current user: {host_repo_config}{hint}"
        )
    if config.state_path.exists() and not can_read_path(config.state_path):
        hint = root_owned_hint(config.state_path)
        reasons.append(f"state file is not readable by current user: {config.state_path}{hint}")
    if not can_write_file(config.state_path):
        hint = root_owned_hint(config.state_path.parent)
        reasons.append(
            f"state file path is not writable by current user: {config.state_path}{hint}"
        )
    return reasons


def analyze_deselect_root_requirements(config: ResolvedManagerConfig) -> list[str]:
    """Return privilege reasons for mutating local state only."""

    reasons: list[str] = []
    if config.state_path.exists() and not can_read_path(config.state_path):
        hint = root_owned_hint(config.state_path)
        reasons.append(f"state file is not readable by current user: {config.state_path}{hint}")
    if not can_write_file(config.state_path):
        hint = root_owned_hint(config.state_path.parent)
        reasons.append(
            f"state file path is not writable by current user: {config.state_path}{hint}"
        )
    return reasons
