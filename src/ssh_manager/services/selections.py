"""State mutation services for selected remote hosts."""

from __future__ import annotations

from ssh_manager.domain.errors import SSHManagerError
from ssh_manager.domain.models import (
    LocalState,
    ManagerConfig,
    RemoteHostDefinition,
    SelectedHostState,
)
from ssh_manager.services.remote_hosts import resolve_selection
from ssh_manager.storage.state_store import load_state, save_state


def load_selected_state(config: ManagerConfig) -> LocalState:
    return load_state(config)


def select_host(
    config: ManagerConfig,
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
    config: ManagerConfig,
    *,
    server_name: str,
) -> tuple[LocalState, SelectedHostState]:
    state = load_state(config)
    removed = state.remove(server_name)
    if removed is None:
        raise SSHManagerError(f"Host '{server_name}' is not selected in local state.")
    save_state(config, state)
    return state, removed
