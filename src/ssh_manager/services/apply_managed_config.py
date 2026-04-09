"""Validate and atomically apply manager-owned SSH config fragments."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from ssh_manager.domain.errors import SSHManagerError
from ssh_manager.domain.models import ManagerConfig
from ssh_manager.ssh_config.parser import parse_ssh_config
from ssh_manager.storage.managed_state import write_managed_config


def validate_managed_config(content: str) -> None:
    try:
        parse_ssh_config(content)
    except Exception as exc:
        raise SSHManagerError(f"Rendered managed config failed parser validation: {exc}") from exc

    ssh_binary = shutil.which("ssh")
    if ssh_binary is None:
        return

    with tempfile.TemporaryDirectory(prefix="ssh-manager-validate-") as temp_dir:
        temp_path = Path(temp_dir) / "ssh-manager.conf"
        temp_path.write_text(content, encoding="utf-8")
        process = subprocess.run(
            [ssh_binary, "-G", "__ssh_manager_probe__", "-F", str(temp_path)],
            capture_output=True,
            text=True,
        )
    if process.returncode != 0:
        stderr = process.stderr.strip() or process.stdout.strip() or "unknown ssh error"
        raise SSHManagerError(f"Rendered managed config failed OpenSSH validation: {stderr}")


def apply_managed_config(
    config: ManagerConfig,
    content: str,
    *,
    backup: bool = True,
) -> Path:
    validate_managed_config(content)
    write_managed_config(config, content, backup=backup)
    return config.managed_config_path
