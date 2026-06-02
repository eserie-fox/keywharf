"""Resolve local state into a desired managed-config preview."""

from __future__ import annotations

import filecmp
from pathlib import Path

from keywharf.config.resolver import ResolvedManagerConfig
from keywharf.domain.errors import KeywharfError
from keywharf.domain.results import ManagedKeyCopyPlan, RenderResult
from keywharf.services.host_definitions import (
    build_host_config_from_selection,
    load_host_definition_list,
    load_host_definition_map,
    validate_host_repo_structure,
    validate_selection,
)
from keywharf.services.host_repo_setup import missing_host_repo_config_message
from keywharf.services.managed_config_renderer import render_managed_config
from keywharf.services.managed_hosts import load_managed_hosts
from keywharf.services.validate import collect_workspace_warnings
from keywharf.storage.ssh_files import list_managed_key_files
from keywharf.storage.state_store import load_state


def render_selected_state(config: ResolvedManagerConfig) -> RenderResult:
    try:
        host_definition_list = load_host_definition_list(config)
    except FileNotFoundError as exc:
        raise KeywharfError(missing_host_repo_config_message(config), exit_code=2) from exc

    structure_validation = validate_host_repo_structure(config, host_definition_list)
    if not structure_validation.ok:
        raise KeywharfError("\n".join(structure_validation.errors))

    state = load_state(config)
    host_definitions = load_host_definition_map(config)
    current_hosts = load_managed_hosts(config)

    selection_errors: list[str] = []
    for selection in state.selected_hosts:
        selection_errors.extend(validate_selection(host_definitions, selection))
    if selection_errors:
        raise KeywharfError("\n".join(selection_errors))

    resolved_selections = []
    desired_hosts = []
    planned_key_copies: list[ManagedKeyCopyPlan] = []
    desired_key_targets: set[Path] = set()

    for selection in state.selected_hosts:
        resolved, host = build_host_config_from_selection(
            config,
            host_definitions,
            selection,
        )
        resolved_selections.append(resolved)
        desired_hosts.append(host)

        source_identity = host.get_ssh_original_identity_file()
        target_identity = host.get_ssh_identity_file()
        if source_identity and target_identity:
            source_path = Path(source_identity).expanduser().resolve()
            target_path = Path(target_identity).expanduser().resolve()
            desired_key_targets.add(target_path)
            if not target_path.exists() or not filecmp.cmp(source_path, target_path, shallow=False):
                planned_key_copies.append(
                    ManagedKeyCopyPlan(
                        source=source_path,
                        target=target_path,
                    )
                )

    existing_key_targets = {
        config.managed_keys_dir / relative_path
        for relative_path in list_managed_key_files(config.managed_keys_dir)
    }
    planned_key_deletes = sorted(
        existing_key_targets - desired_key_targets,
        key=lambda item: item.as_posix(),
    )

    desired_hosts.sort(key=lambda host: host.name or "")
    content = render_managed_config(desired_hosts)
    current_hosts.sort(key=lambda host: host.name or "")
    state_names = {item.server_name for item in state.selected_hosts}
    orphaned_hosts = sorted(
        host.name for host in current_hosts if host.name and host.name not in state_names
    )

    return RenderResult(
        content=content,
        resolved_hosts=desired_hosts,
        resolved_selections=resolved_selections,
        planned_key_copies=planned_key_copies,
        planned_key_deletes=planned_key_deletes,
        warnings=collect_workspace_warnings(config, state=state, current_hosts=current_hosts),
        orphaned_hosts=orphaned_hosts,
        in_sync=_managed_output_matches(current_hosts, desired_hosts)
        and not planned_key_copies
        and not planned_key_deletes,
    )


def _managed_output_matches(current_hosts, desired_hosts) -> bool:
    if len(current_hosts) != len(desired_hosts):
        return False
    return [host.to_dict() for host in current_hosts] == [host.to_dict() for host in desired_hosts]
