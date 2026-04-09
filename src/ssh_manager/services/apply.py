"""Apply the desired local state to manager-owned files."""

from __future__ import annotations

from ssh_manager.domain.errors import SSHManagerError
from ssh_manager.domain.models import ManagerConfig
from ssh_manager.domain.results import ApplyResult
from ssh_manager.services.apply_managed_config import apply_managed_config
from ssh_manager.services.local_hosts import load_managed_hosts
from ssh_manager.services.render import render_selected_state
from ssh_manager.storage.ssh_files import copy_identity_file, delete_identity_file


def apply_selected_state(
    config: ManagerConfig,
    *,
    backup: bool = True,
    dry_run: bool = False,
    allow_empty: bool = False,
) -> ApplyResult:
    render_result = render_selected_state(config)
    current_hosts = load_managed_hosts(config)
    if not allow_empty and not render_result.resolved_hosts and current_hosts:
        raise SSHManagerError(
            "Local state is empty while managed config still contains hosts. "
            "Re-select hosts before apply, or pass --allow-empty to clear the managed output."
        )

    changed = (
        not render_result.in_sync
        or bool(render_result.planned_key_copies)
        or bool(render_result.planned_key_deletes)
    )
    if dry_run:
        return ApplyResult(
            managed_config_path=config.managed_config_path,
            render_result=render_result,
            warnings=render_result.warnings,
            changed=changed,
            dry_run=True,
        )

    copied_keys = []
    for plan in render_result.planned_key_copies:
        copy_identity_file(plan.source, plan.target)
        copied_keys.append(plan.target)

    apply_managed_config(config, render_result.content, backup=backup)

    deleted_keys = []
    for target in render_result.planned_key_deletes:
        delete_identity_file(target)
        deleted_keys.append(target)

    return ApplyResult(
        managed_config_path=config.managed_config_path,
        render_result=render_result,
        copied_keys=copied_keys,
        deleted_keys=deleted_keys,
        warnings=render_result.warnings,
        changed=changed,
        dry_run=False,
    )
