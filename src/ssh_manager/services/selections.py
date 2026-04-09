"""State mutation services for selected remote hosts."""

from __future__ import annotations

from ssh_manager.config.resolver import ResolvedManagerConfig
from ssh_manager.domain.errors import SSHManagerError
from ssh_manager.domain.models import (
    LocalState,
    RemoteHostDefinition,
    SelectedHostState,
)
from ssh_manager.services.privilege import can_read_path, can_write_file, root_owned_hint
from ssh_manager.services.remote_hosts import resolve_selection
from ssh_manager.services.remote_hosts import remote_config_path
from ssh_manager.storage.state_store import load_state, save_state


def load_selected_state(config: ResolvedManagerConfig) -> LocalState:
    return load_state(config)


def select_host(
    config: ResolvedManagerConfig,
    remote_hosts: dict[str, RemoteHostDefinition],
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
    resolve_selection(remote_hosts, selection)

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
        raise SSHManagerError(f"Host '{server_name}' is not selected in local state.")
    save_state(config, state)
    return state, removed


def analyze_select_root_requirements(config: ResolvedManagerConfig) -> list[str]:
    """Return privilege reasons for mutating local state from remote data."""

    reasons: list[str] = []
    remote_config = remote_config_path(config)
    if remote_config.exists() and not can_read_path(remote_config):
        reasons.append(
            f"remote repository config is not readable by current user: {remote_config}{root_owned_hint(remote_config)}"
        )
    if config.state_path.exists() and not can_read_path(config.state_path):
        reasons.append(
            f"state file is not readable by current user: {config.state_path}{root_owned_hint(config.state_path)}"
        )
    if not can_write_file(config.state_path):
        reasons.append(
            f"state file path is not writable by current user: {config.state_path}{root_owned_hint(config.state_path.parent)}"
        )
    return reasons


def analyze_deselect_root_requirements(config: ResolvedManagerConfig) -> list[str]:
    """Return privilege reasons for mutating local state only."""

    reasons: list[str] = []
    if config.state_path.exists() and not can_read_path(config.state_path):
        reasons.append(
            f"state file is not readable by current user: {config.state_path}{root_owned_hint(config.state_path)}"
        )
    if not can_write_file(config.state_path):
        reasons.append(
            f"state file path is not writable by current user: {config.state_path}{root_owned_hint(config.state_path.parent)}"
        )
    return reasons
