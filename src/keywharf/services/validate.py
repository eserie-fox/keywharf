"""Validation service for config, host definitions, and local desired state."""

from __future__ import annotations

from keywharf.config.resolver import ResolvedManagerConfig
from keywharf.domain.results import ValidationResult
from keywharf.services.host_definitions import (
    load_host_definition_list,
    load_host_definition_map,
    validate_host_definitions,
    validate_selection,
)
from keywharf.services.host_repo_setup import missing_host_repo_config_message
from keywharf.services.install_include import detect_include
from keywharf.services.managed_hosts import load_managed_hosts
from keywharf.storage.state_store import load_state


def validate_workspace(config: ResolvedManagerConfig) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []

    try:
        host_definitions = load_host_definition_list(config)
    except FileNotFoundError:
        return ValidationResult(ok=False, errors=[missing_host_repo_config_message(config)])

    host_definition_validation = validate_host_definitions(config, host_definitions)
    errors.extend(host_definition_validation.errors)

    try:
        state = load_state(config)
    except Exception as exc:
        errors.append(str(exc))
        state = None

    host_definition_map = None
    if not errors:
        try:
            host_definition_map = load_host_definition_map(config)
        except Exception as exc:
            errors.append(str(exc))

    current_hosts = []
    try:
        current_hosts = load_managed_hosts(config)
    except Exception as exc:
        errors.append(f"Current managed config could not be parsed: {exc}")

    if state is not None and host_definition_map is not None:
        for selection in state.selected_hosts:
            errors.extend(validate_selection(host_definition_map, selection))

    if not detect_include(config):
        warnings.append(
            f"Main SSH config does not include {config.managed_config_path}. "
            "Run 'keywharf install-include' or add the Include line manually."
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
                "Re-select hosts before apply, or use 'keywharf apply --allow-empty' to clear it."
            )

    return ValidationResult(ok=not errors, errors=errors, warnings=warnings)
