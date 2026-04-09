"""Validate and atomically apply manager-owned SSH config fragments."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from keywharf.config.resolver import ResolvedManagerConfig
from keywharf.domain.errors import KeywharfError
from keywharf.ssh_config.parser import parse_ssh_config
from keywharf.storage.managed_files import write_managed_config


def validate_managed_config(content: str) -> None:
    try:
        parse_ssh_config(content)
    except Exception as exc:
        raise KeywharfError(f"Rendered managed config failed parser validation: {exc}") from exc

    ssh_binary = shutil.which("ssh")
    if ssh_binary is None:
        return

    with tempfile.TemporaryDirectory(prefix="keywharf-validate-") as temp_dir:
        temp_path = Path(temp_dir) / "keywharf.conf"
        temp_path.write_text(content, encoding="utf-8")
        process = subprocess.run(
            [ssh_binary, "-G", "__keywharf_probe__", "-F", str(temp_path)],
            capture_output=True,
            text=True,
        )
    if process.returncode != 0:
        stderr = process.stderr.strip() or process.stdout.strip() or "unknown ssh error"
        raise KeywharfError(f"Rendered managed config failed OpenSSH validation: {stderr}")


def apply_managed_config(
    config: ResolvedManagerConfig,
    content: str,
    *,
    backup: bool = True,
) -> Path:
    validate_managed_config(content)
    write_managed_config(config, content, backup=backup)
    return config.managed_config_path
