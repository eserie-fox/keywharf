"""Data-root and token-expansion helpers."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Mapping


DATA_ROOT_ENV = "KEYWHARF_DATA_ROOT"
DATA_ROOT_MARKER = "KEYWHARF_DATA_ROOT"
DATA_ROOT_TOKEN = "%{DATA_ROOT}"
DEFAULT_HOME_WORKSPACE_DIRNAME = "keywharf"
DEFAULT_CONFIG_FILE_NAME = "config.json"


def _existing_path(raw_value: str, *, label: str) -> Path:
    candidate = Path(raw_value).expanduser().resolve()
    if not candidate.exists():
        raise RuntimeError(f"{label} points to a non-existent path: {candidate}")
    return candidate


def workspace_marker_path(root: Path) -> Path:
    return root / DATA_ROOT_MARKER


def default_workspace_config_path(root: Path) -> Path:
    return root / DEFAULT_CONFIG_FILE_NAME


def is_workspace_root(root: Path) -> bool:
    candidate = root.expanduser().resolve()
    return workspace_marker_path(candidate).is_file() and default_workspace_config_path(candidate).is_file()


def default_home_workspace(home: Path | None = None) -> Path:
    home_dir = (home or Path.home()).expanduser().resolve()
    return (home_dir / DEFAULT_HOME_WORKSPACE_DIRNAME).resolve()


def _candidate_reason(root: Path) -> str | None:
    if not root.exists():
        return "directory does not exist"
    if not root.is_dir():
        return "path is not a directory"
    marker_path = workspace_marker_path(root)
    if not marker_path.is_file():
        return f"missing marker file {marker_path.name}"
    config_path = default_workspace_config_path(root)
    if not config_path.is_file():
        return f"missing config file {config_path.name}"
    return None


def _format_attempts(attempts: list[str]) -> str:
    return (
        "Unable to locate keywharf data root.\n"
        "Search order:\n"
        + "\n".join(f"- {item}" for item in attempts)
        + f"\nSet {DATA_ROOT_ENV}, pass --data-root, or run 'keywharf init'."
    )


def resolve_data_root(
    *,
    cwd: Path | None = None,
    home: Path | None = None,
    env: Mapping[str, str] | None = None,
) -> Path:
    """Resolve the data root without import-time side effects."""

    env_map = env or os.environ
    current_dir = (cwd or Path.cwd()).resolve()
    home_dir = (home or Path.home()).resolve()
    attempts: list[str] = []

    configured_env = env_map.get(DATA_ROOT_ENV)
    if configured_env:
        try:
            return _existing_path(configured_env, label=DATA_ROOT_ENV)
        except RuntimeError as exc:
            attempts.append(str(exc))
            raise RuntimeError(_format_attempts(attempts)) from exc

    current_reason = _candidate_reason(current_dir)
    attempts.append(
        f"current directory {current_dir}: {'usable workspace root' if current_reason is None else current_reason}"
    )
    if current_reason is None:
        return current_dir

    ancestor_with_marker = False
    for parent in current_dir.parents:
        marker_path = workspace_marker_path(parent)
        if not marker_path.is_file():
            continue
        ancestor_with_marker = True
        reason = _candidate_reason(parent)
        attempts.append(
            f"workspace ancestor {parent}: {'usable workspace root' if reason is None else reason}"
        )
        if reason is None:
            return parent
    if not ancestor_with_marker:
        attempts.append(f"workspace ancestors of {current_dir}: no {DATA_ROOT_MARKER} marker found")

    home_workspace = default_home_workspace(home_dir)
    home_reason = _candidate_reason(home_workspace)
    attempts.append(
        f"home default {home_workspace}: {'usable workspace root' if home_reason is None else home_reason}"
    )
    if home_reason is None:
        return home_workspace

    raise RuntimeError(_format_attempts(attempts))


def expand_data_root(value: str | Path | None, data_root: Path) -> str | Path | None:
    """Expand %{DATA_ROOT} in strings or paths."""

    if value is None:
        return None

    text = str(value)
    if DATA_ROOT_TOKEN not in text:
        return value

    expanded = text.replace(DATA_ROOT_TOKEN, str(data_root))
    return Path(expanded) if isinstance(value, Path) else expanded
