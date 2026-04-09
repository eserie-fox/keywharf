"""Data-root and token-expansion helpers."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Mapping


DATA_ROOT_ENV = "SSH_MANAGER_DATA_ROOT"
DATA_ROOT_MARKER = "SSH_MANAGER_DATA_ROOT"
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

    configured_env = env_map.get(DATA_ROOT_ENV)
    if configured_env:
        return _existing_path(configured_env, label=DATA_ROOT_ENV)

    marker_root = _find_marker(DATA_ROOT_MARKER, cwd=current_dir, home=home_dir)
    if marker_root is not None:
        return marker_root

    raise RuntimeError(
        f"Unable to locate data root. Set {DATA_ROOT_ENV} or create a {DATA_ROOT_MARKER} marker file."
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
