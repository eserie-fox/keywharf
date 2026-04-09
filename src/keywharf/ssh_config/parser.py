"""Low-level parser for SSH config text."""

from __future__ import annotations

from keywharf.domain.models import SSHHostConfig
from keywharf.storage.ssh_files import MANAGED_SSH_HEADER


def parse_ssh_config(ssh_config_content: str) -> list[SSHHostConfig]:
    hosts: list[SSHHostConfig] = []
    current: SSHHostConfig | None = None
    pending_comments: list[str] = []

    for lineno, raw_line in enumerate(ssh_config_content.splitlines(), start=1):
        stripped = raw_line.strip()
        if not stripped:
            continue
        if stripped == MANAGED_SSH_HEADER:
            continue
        if stripped.startswith("#"):
            pending_comments.append(stripped[1:].strip())
            continue

        key, separator, remainder = stripped.partition(" ")
        if not separator:
            raise ValueError(f"Invalid SSH config line {lineno}: {raw_line}")

        value = remainder.strip()
        comment = " ".join(item for item in pending_comments if item).strip()

        if key == "Host":
            if current is not None:
                hosts.append(current)
            current = SSHHostConfig(name=value, comment=comment or None)
            pending_comments = []
            continue

        if current is None:
            raise ValueError(f"Unexpected SSH config line before Host at line {lineno}: {raw_line}")

        current.add_config(key, value, comment)
        pending_comments = []

    if current is not None:
        hosts.append(current)

    return hosts
