"""Filesystem permission helpers for mutating ssh-manager commands."""

from __future__ import annotations

import os
from pathlib import Path


def can_write_directory(path: Path) -> bool:
    if path.exists():
        return path.is_dir() and _has_write_execute(path)
    return _has_write_execute(_nearest_existing_parent(path))


def can_write_file(path: Path) -> bool:
    if path.exists():
        return os.access(path, os.W_OK)
    return _has_write_execute(_nearest_existing_parent(path.parent))


def can_read_path(path: Path) -> bool:
    if not path.exists():
        return False
    if path.is_dir():
        return os.access(path, os.R_OK | os.X_OK)
    return os.access(path, os.R_OK)


def can_delete_path(path: Path) -> bool:
    if not path.exists():
        return True
    resolved = path.resolve()
    if resolved.is_dir() and not resolved.is_symlink():
        return _has_write_execute(resolved.parent) and _has_write_execute(resolved)
    return _has_write_execute(resolved.parent)


def root_owned_hint(path: Path) -> str:
    try:
        owner_uid = path.stat(follow_symlinks=False).st_uid
    except OSError:
        return ""
    if owner_uid == 0:
        return " (existing target is owned by root)"
    return ""


def _nearest_existing_parent(path: Path) -> Path:
    probe = path.resolve()
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    return probe


def _has_write_execute(path: Path) -> bool:
    return os.access(path, os.W_OK | os.X_OK)
