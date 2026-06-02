"""Read-only local status views derived from state and managed output."""

from __future__ import annotations

from keywharf.config.resolver import ResolvedManagerConfig
from keywharf.domain.errors import KeywharfError
from keywharf.domain.results import LocalHostStatus
from keywharf.services.host_definitions import (
    build_host_config_from_selection,
    load_host_definition_map,
)
from keywharf.services.managed_hosts import load_managed_hosts
from keywharf.storage.state_store import load_state


def list_local_statuses(config: ResolvedManagerConfig) -> list[LocalHostStatus]:
    state = load_state(config)
    current_hosts = load_managed_hosts(config)
    current_by_name = {host.name: host for host in current_hosts if host.name is not None}

    host_definitions = None
    host_repo_error = None
    try:
        host_definitions = load_host_definition_map(config)
    except Exception as exc:
        host_repo_error = str(exc)

    statuses: list[LocalHostStatus] = []
    for selection in state.selected_hosts:
        current_host = current_by_name.pop(selection.server_name, None)
        if host_definitions is None:
            statuses.append(
                LocalHostStatus(
                    server_name=selection.server_name,
                    status="invalid",
                    selection=selection,
                    current_host=current_host,
                    reason=host_repo_error,
                )
            )
            continue

        try:
            resolved, desired_host = build_host_config_from_selection(
                config,
                host_definitions,
                selection,
            )
        except Exception as exc:
            statuses.append(
                LocalHostStatus(
                    server_name=selection.server_name,
                    status="invalid",
                    selection=selection,
                    current_host=current_host,
                    reason=str(exc),
                )
            )
            continue

        status = "pending"
        if current_host is not None and current_host.to_dict() == desired_host.to_dict():
            status = "applied"
        statuses.append(
            LocalHostStatus(
                server_name=selection.server_name,
                status=status,
                selection=selection,
                desired_host=desired_host,
                current_host=current_host,
                resolved_selection=resolved,
            )
        )

    for name, current_host in sorted(current_by_name.items()):
        statuses.append(
            LocalHostStatus(
                server_name=name,
                status="orphaned",
                current_host=current_host,
                reason="Managed config contains this host, but local state does not.",
            )
        )

    statuses.sort(key=lambda item: (item.server_name, item.status))
    return statuses


def get_local_status(config: ResolvedManagerConfig, server_name: str) -> LocalHostStatus:
    for item in list_local_statuses(config):
        if item.server_name == server_name:
            return item
    raise KeywharfError(f"No local host named '{server_name}' found in state or managed config.")
