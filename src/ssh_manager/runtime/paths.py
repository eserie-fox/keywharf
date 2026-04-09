"""Data-root and path-resolution helpers."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Mapping


PRIMARY_DATA_ROOT_ENV = "SSH_MANAGER_DATA_ROOT"
LEGACY_DATA_ROOT_ENV = "SSH_CONFIG_DATA_ROOT"
PRIMARY_DATA_ROOT_MARKER = "SSH_MANAGER_DATA_ROOT"
LEGACY_DATA_ROOT_MARKER = "SSH_CONFIG_DATA_ROOT"
DATA_ROOT_TOKEN = "%{DATA_ROOT}"


def _existing_path(raw_value: str, *, label: str) -> Path:
    candidate = Path(raw_value).expanduser().resolve()
    if not candidate.exists():
        raise RuntimeError(f"{label} points to a non-existent path: {candidate}")
    return candidate


def _iter_search_roots(cwd: Path, home: Path) -> list[Path]:
    candidates: list[Path] = []
    seen: set[Path] = set()
    for candidate in (cwd.resolve(), *cwd.resolve().parents, home.resolve()):
        if candidate not in seen:
            candidates.append(candidate)
            seen.add(candidate)
    return candidates


def _find_marker(marker_name: str, *, cwd: Path, home: Path) -> Path | None:
    for base in _iter_search_roots(cwd, home):
        if (base / marker_name).is_file():
            return base
    for base in _iter_search_roots(cwd, home):
        if not base.is_dir():
            continue
        for child in sorted((item for item in base.iterdir() if item.is_dir()), key=lambda item: item.name):
            if (child / marker_name).is_file():
                return child
    return None


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

    primary_env = env_map.get(PRIMARY_DATA_ROOT_ENV)
    if primary_env:
        return _existing_path(primary_env, label=PRIMARY_DATA_ROOT_ENV)

    primary_marker = _find_marker(PRIMARY_DATA_ROOT_MARKER, cwd=current_dir, home=home_dir)
    if primary_marker is not None:
        return primary_marker

    legacy_env = env_map.get(LEGACY_DATA_ROOT_ENV)
    if legacy_env:
        return _existing_path(legacy_env, label=LEGACY_DATA_ROOT_ENV)

    legacy_marker = _find_marker(LEGACY_DATA_ROOT_MARKER, cwd=current_dir, home=home_dir)
    if legacy_marker is not None:
        return legacy_marker

    raise RuntimeError(
        "Unable to locate data root. Set SSH_MANAGER_DATA_ROOT or create an "
        "SSH_MANAGER_DATA_ROOT marker file. Legacy SSH_CONFIG_DATA_ROOT is still "
        "accepted for compatibility."
    )


def expand_data_root(value: str | Path | None, data_root: Path) -> str | Path | None:
    """Expand %{DATA_ROOT} in strings or paths."""

    if value is None:
        return None

    text = str(value)
    if DATA_ROOT_TOKEN not in text:
        return value

    expanded = text.replace(DATA_ROOT_TOKEN, str(data_root))
    return Path(expanded) if isinstance(value, Path) else expanded
