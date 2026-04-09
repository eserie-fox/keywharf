"""Apply the desired local state to manager-owned files."""

from __future__ import annotations

from keywharf.config.resolver import ResolvedManagerConfig
from keywharf.domain.errors import KeywharfError
from keywharf.domain.results import ApplyResult
from keywharf.services.managed_config_applier import apply_managed_config
from keywharf.services.managed_hosts import load_managed_hosts
from keywharf.services.privilege import (
    can_delete_path,
    can_read_path,
    can_write_directory,
    can_write_file,
    root_owned_hint,
)
from keywharf.services.render import render_selected_state
from keywharf.storage.remote_repo import remote_repo_config_path
from keywharf.storage.ssh_files import copy_identity_file, delete_identity_file


def apply_selected_state(
    config: ResolvedManagerConfig,
    *,
    backup: bool = True,
    dry_run: bool = False,
    allow_empty: bool = False,
) -> ApplyResult:
    render_result = render_selected_state(config)
    current_hosts = load_managed_hosts(config)
    if not allow_empty and not render_result.resolved_hosts and current_hosts:
        raise KeywharfError(
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


def analyze_apply_root_requirements(
    config: ResolvedManagerConfig,
    render_result,
    *,
    backup: bool = True,
) -> list[str]:
    """Return concrete privilege reasons for one apply plan."""

    reasons: list[str] = []
    remote_config = remote_repo_config_path(config)

    for path, label in (
        (config.state_path, "state file"),
        (remote_config, "remote repository config"),
        (config.managed_config_path, "managed config"),
    ):
        if path.exists() and not can_read_path(path):
            reasons.append(
                f"{label} is not readable by current user: {path}{root_owned_hint(path)}"
            )

    if not can_write_file(config.managed_config_path):
        reasons.append(
            f"managed config path is not writable by current user: {config.managed_config_path}{root_owned_hint(config.managed_config_path.parent)}"
        )
    if not can_write_directory(config.managed_keys_dir):
        reasons.append(
            f"managed keys directory is not writable by current user: {config.managed_keys_dir}{root_owned_hint(config.managed_keys_dir)}"
        )
    if backup and config.managed_config_path.exists() and not can_write_directory(config.managed_config_path.parent):
        reasons.append(
            f"managed config backup directory is not writable by current user: {config.managed_config_path.parent}{root_owned_hint(config.managed_config_path.parent)}"
        )

    for plan in render_result.planned_key_copies:
        if not can_read_path(plan.source):
            reasons.append(
                f"identity source is not readable by current user: {plan.source}{root_owned_hint(plan.source)}"
            )
        if not can_write_file(plan.target):
            reasons.append(
                f"managed key target path is not writable by current user: {plan.target}{root_owned_hint(plan.target.parent)}"
            )

    for target in render_result.planned_key_deletes:
        if not can_delete_path(target):
            reasons.append(
                f"managed key path is not removable by current user: {target}{root_owned_hint(target)}"
            )

    return reasons
