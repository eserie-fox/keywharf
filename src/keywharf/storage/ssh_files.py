"""Filesystem helpers for local SSH config and copied identities."""

from __future__ import annotations

import os
import shutil
import stat
from datetime import datetime
from pathlib import Path

MANAGED_SSH_HEADER = "# This file is managed by keywharf"


def list_ssh_key_files(ssh_dir: Path) -> list[str]:
    ignore = {"authorized_keys", "config", "known_hosts", "known_hosts.old"}
    if not ssh_dir.exists():
        return []
    results: list[str] = []
    for item in ssh_dir.iterdir():
        name = item.name
        if name in ignore or name.endswith(".pub"):
            continue
        results.append(name)
    return results


def list_managed_key_files(managed_keys_dir: Path) -> list[str]:
    if not managed_keys_dir.exists():
        return []
    return sorted(
        path.relative_to(managed_keys_dir).as_posix()
        for path in managed_keys_dir.rglob("*")
        if path.is_file() and not path.name.endswith(".pub")
    )


def read_ssh_config(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def write_ssh_config(path: Path, content: str, *, backup: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f"{path.name}.tmp")

    with tmp_path.open("w", encoding="utf-8") as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())

    if backup and path.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = path.with_name(f"{path.name}.bak.{timestamp}")
        shutil.copy2(path, backup_path)

    try:
        os.replace(tmp_path, path)
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink()
        raise


def copy_identity_file(source: str | Path | None, target: str | Path | None) -> None:
    if source is None or target is None:
        return

    source_path = Path(source).expanduser()
    target_path = Path(target).expanduser()

    if not source_path.exists():
        raise FileNotFoundError(source_path)

    target_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, target_path)
    os.chmod(target_path, stat.S_IRUSR | stat.S_IWUSR)


def delete_identity_file(path: str | Path | None) -> None:
    if path is None:
        return

    target = Path(path).expanduser()
    if target.is_file():
        target.unlink()
    parent = target.parent
    if parent.is_dir() and not any(parent.iterdir()):
        parent.rmdir()
