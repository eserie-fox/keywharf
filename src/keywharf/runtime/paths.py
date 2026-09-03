"""Workspace-root and token-expansion helpers."""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

WORKSPACE_ENV = "KEYWHARF_WORKSPACE"
WORKSPACE_MARKER = "KEYWHARF_WORKSPACE"
WORKSPACE_TOKEN = "%{WORKSPACE}"
DEFAULT_CONFIG_FILE_NAME = "config.json"


def _existing_path(raw_value: str, *, label: str) -> Path:
    candidate = Path(raw_value).expanduser().resolve()
    if not candidate.exists():
        raise RuntimeError(f"{label} points to a non-existent path: {candidate}")
    return candidate


def workspace_marker_path(root: Path) -> Path:
    return root / WORKSPACE_MARKER


def default_workspace_config_path(root: Path) -> Path:
    return root / DEFAULT_CONFIG_FILE_NAME


def has_workspace_marker(root: Path) -> bool:
    try:
        return workspace_marker_path(root.expanduser().resolve()).is_file()
    except OSError:
        return False


def _format_attempts(attempts: list[Path]) -> str:
    lines = "\n".join(f"- {item}" for item in attempts)
    return (
        "Unable to locate keywharf workspace.\n"
        f"Searched for {WORKSPACE_MARKER} in these directories:\n"
        f"{lines}\n"
        f"Pass --workspace, set {WORKSPACE_ENV}, or create a workspace with "
        "'keywharf init <workspace_name>'."
    )


def _search_bases(current_dir: Path, home_dir: Path) -> list[Path]:
    bases = [current_dir, *current_dir.parents, home_dir]
    ordered: list[Path] = []
    seen: set[Path] = set()
    for base in bases:
        resolved = base.expanduser().resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        ordered.append(resolved)
    return ordered


def _accessible_child_dirs(root: Path) -> list[Path]:
    try:
        children = list(root.iterdir())
    except OSError:
        return []

    directories: list[Path] = []
    for child in sorted(children, key=lambda item: item.name):
        try:
            if child.is_dir():
                directories.append(child.resolve())
        except OSError:
            continue
    return directories


def resolve_workspace_root(
    *,
    cwd: Path | None = None,
    home: Path | None = None,
    env: Mapping[str, str] | None = None,
) -> Path:
    """Resolve the workspace root without import-time side effects."""

    env_map = env or os.environ
    current_dir = (cwd or Path.cwd()).resolve()
    home_dir = (home or Path.home()).resolve()

    configured_env = env_map.get(WORKSPACE_ENV)
    if configured_env:
        return _existing_path(configured_env, label=WORKSPACE_ENV)

    checked: list[Path] = []
    seen_checked: set[Path] = set()
    for base in _search_bases(current_dir, home_dir):
        for child in _accessible_child_dirs(base):
            if child not in seen_checked:
                checked.append(child)
                seen_checked.add(child)
            if has_workspace_marker(child):
                return child
        if base not in seen_checked:
            checked.append(base)
            seen_checked.add(base)
        if has_workspace_marker(base):
            return base

    raise RuntimeError(_format_attempts(checked))


def expand_workspace_root(
    value: str | Path | None,
    workspace_root: Path,
) -> str | Path | None:
    """Expand %{WORKSPACE} in strings or paths."""

    if value is None:
        return None

    text = str(value)
    if WORKSPACE_TOKEN not in text:
        return value

    expanded = Path(text.replace(WORKSPACE_TOKEN, str(workspace_root)))
    return expanded if isinstance(value, Path) else str(expanded)
