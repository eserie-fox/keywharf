"""Validation service for config, host repo, and local desired state."""

from __future__ import annotations

from keywharf.config.resolver import ResolvedManagerConfig
from keywharf.domain.models import HostDefinition
from keywharf.domain.results import ValidationResult
from keywharf.services.host_definitions import (
    collect_incomplete_host_errors,
    incomplete_host_guidance,
    load_host_definition_list,
    validate_host_repo_structure,
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

    structure_validation = validate_host_repo_structure(config, host_definitions)
    errors.extend(structure_validation.errors)

    incomplete_errors, incomplete_hosts = collect_incomplete_host_errors(host_definitions)
    errors.extend(incomplete_errors)
    if incomplete_errors:
        errors.append(incomplete_host_guidance())

    try:
        state = load_state(config)
    except Exception as exc:
        errors.append(str(exc))
        state = None

    host_definition_map = _build_host_definition_map(host_definitions)

    current_hosts = []
    try:
        current_hosts = load_managed_hosts(config)
    except Exception as exc:
        errors.append(f"Current managed config could not be parsed: {exc}")

    if state is not None and host_definition_map is not None:
        for selection in state.selected_hosts:
            if selection.server_name in incomplete_hosts:
                continue
            errors.extend(validate_selection(host_definition_map, selection))

    warnings.extend(_collect_workspace_warnings(config, state=state, current_hosts=current_hosts))
    return ValidationResult(
        ok=not errors,
        errors=list(dict.fromkeys(errors)),
        warnings=list(dict.fromkeys(warnings)),
    )


def collect_workspace_warnings(
    config: ResolvedManagerConfig,
    *,
    state,
    current_hosts,
) -> list[str]:
    return _collect_workspace_warnings(config, state=state, current_hosts=current_hosts)


def _build_host_definition_map(
    host_definitions: list[HostDefinition],
) -> dict[str, HostDefinition] | None:
    mapping: dict[str, HostDefinition] = {}
    for host_definition in host_definitions:
        server_name = host_definition.server_name
        if server_name is None or server_name in mapping:
            return None
        mapping[server_name] = host_definition
    return mapping


def _collect_workspace_warnings(
    config: ResolvedManagerConfig,
    *,
    state,
    current_hosts,
) -> list[str]:
    warnings: list[str] = []

    if not detect_include(config):
        warnings.append(
            f"Main SSH config does not include {config.managed_config_path}. "
            "Run 'keywharf install-include' or add the Include line manually."
        )

    if state is None:
        return warnings

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

    return warnings
