"""Formal manager-config loading helpers."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from keywharf.config.merge import config_deep_merge
from keywharf.config.models import ManagerConfig
from keywharf.config.resolver import ResolvedManagerConfig, resolve_manager_config
from keywharf.config.resources import read_json_mapping
from keywharf.runtime.paths import DEFAULT_CONFIG_FILE_NAME, resolve_workspace_root

MANAGER_DEFAULTS_RESOURCE_SPEC = "pkg://keywharf/config_defaults/manager.json"


def load_manager_defaults() -> dict[str, Any]:
    """Load package-shipped manager config defaults."""

    return read_json_mapping(MANAGER_DEFAULTS_RESOURCE_SPEC)


def merge_manager_config_mapping(data: Mapping[str, Any]) -> dict[str, Any]:
    """Merge one override mapping over package defaults."""

    return config_deep_merge(load_manager_defaults(), dict(data))


def resolve_config_path(
    config_override: Path | None = None,
    *,
    workspace_root: Path | None = None,
    cwd: Path | None = None,
    home: Path | None = None,
    env: Mapping[str, str] | None = None,
) -> Path:
    """Resolve the manager-config path from CLI/runtime context."""

    if config_override is None:
        resolved_workspace_root = workspace_root or resolve_workspace_root(
            cwd=cwd,
            home=home,
            env=env,
        )
        return (resolved_workspace_root / DEFAULT_CONFIG_FILE_NAME).resolve()

    candidate = Path(config_override).expanduser()
    if candidate.is_absolute():
        return candidate.resolve()

    resolved_workspace_root = workspace_root or resolve_workspace_root(
        cwd=cwd,
        home=home,
        env=env,
    )
    return (resolved_workspace_root / candidate).resolve()


def load_resolved_manager_config(
    config_override: Path | None = None,
    *,
    workspace_root: Path | None = None,
    cwd: Path | None = None,
    home: Path | None = None,
    env: Mapping[str, str] | None = None,
) -> ResolvedManagerConfig:
    """Load defaults-aware manager config and resolve runtime paths."""

    resolved_workspace_root = (
        workspace_root.expanduser().resolve() if workspace_root is not None else None
    )
    absolute_override = None
    if config_override is not None:
        candidate = Path(config_override).expanduser()
        if candidate.is_absolute():
            absolute_override = candidate.resolve()
    if resolved_workspace_root is None:
        resolved_workspace_root = (
            absolute_override.parent
            if absolute_override is not None
            else resolve_workspace_root(cwd=cwd, home=home, env=env)
        )
    if absolute_override is not None and not absolute_override.is_relative_to(
        resolved_workspace_root
    ):
        raise RuntimeError(
            f"Absolute --config path {absolute_override} is outside workspace root "
            f"{resolved_workspace_root}."
        )

    config_path = resolve_config_path(
        config_override,
        workspace_root=resolved_workspace_root,
        cwd=cwd,
        home=home,
        env=env,
    )
    raw_config = ManagerConfig.from_file(config_path)
    return resolve_manager_config(
        raw_config,
        config_path=config_path,
        workspace_root=resolved_workspace_root,
    )
