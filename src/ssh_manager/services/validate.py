"""Validation service for config, remote definitions, and local desired state."""

from __future__ import annotations

from ssh_manager.domain.results import ValidationResult
from ssh_manager.services.install_include import detect_include
from ssh_manager.services.local_hosts import load_managed_hosts
from ssh_manager.services.remote_hosts import (
    load_remote_host_list,
    load_remote_host_map,
    validate_selection,
    validate_remote_host_definitions,
)
from ssh_manager.storage.state_store import load_state


def validate_workspace(config) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []

    try:
        remote_hosts_list = load_remote_host_list(config)
    except FileNotFoundError:
        return ValidationResult(
            ok=False,
            errors=[
                "Remote repository config not found. Run 'ssh-manager pull' to clone or sync it first."
            ],
        )

    remote_validation = validate_remote_host_definitions(config, remote_hosts_list)
    errors.extend(remote_validation.errors)

    try:
        state = load_state(config)
    except Exception as exc:
        errors.append(str(exc))
        state = None

    remote_hosts_map = None
    if not errors:
        try:
            remote_hosts_map = load_remote_host_map(config)
        except Exception as exc:
            errors.append(str(exc))

    current_hosts = []
    try:
        current_hosts = load_managed_hosts(config)
    except Exception as exc:
        errors.append(f"Current managed config could not be parsed: {exc}")

    if state is not None and remote_hosts_map is not None:
        for selection in state.selected_hosts:
            errors.extend(validate_selection(remote_hosts_map, selection))

    if not detect_include(config):
        warnings.append(
            f"Main SSH config does not include {config.managed_config_path}. "
            "Run 'ssh-manager install-include' or add the Include line manually."
        )

    if state is not None:
        state_names = {item.server_name for item in state.selected_hosts}
        current_names = {item.name for item in current_hosts if item.name}
        orphaned = sorted(name for name in current_names - state_names if name)
        if orphaned:
            warnings.append(
                "Managed config contains orphaned hosts not present in local state: "
                + ", ".join(orphaned)
            )
        if not state.selected_hosts and current_names:
            warnings.append(
                "Local state is empty while managed config still contains hosts. "
                "Re-select hosts before apply, or use 'ssh-manager apply --allow-empty' to clear it."
            )

    return ValidationResult(ok=not errors, errors=errors, warnings=warnings)
