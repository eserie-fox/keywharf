"""Parser for Keywharf's managed fragment, including its legacy single-name format."""

from __future__ import annotations

from keywharf.domain.models import SSHHostConfig, normalize_host_names, validate_ssh_name
from keywharf.ssh_config.render import OWNER_COMMENT, validate_managed_hosts
from keywharf.storage.ssh_files import MANAGED_SSH_HEADER


def parse_ssh_config(ssh_config_content: str) -> list[SSHHostConfig]:
    hosts: list[SSHHostConfig] = []
    current: SSHHostConfig | None = None
    pending_comments: list[str] = []
    pending_owner: str | None = None

    for lineno, raw_line in enumerate(ssh_config_content.splitlines(), start=1):
        stripped = raw_line.strip()
        if not stripped or stripped == MANAGED_SSH_HEADER:
            continue
        if stripped.startswith("#") and stripped[1:].strip().casefold().startswith(
            "keywharf-owner"
        ):
            if pending_owner is not None or not stripped.startswith(OWNER_COMMENT):
                raise ValueError(f"Malformed or duplicate managed ownership at line {lineno}")
            pending_owner = validate_ssh_name(stripped[len(OWNER_COMMENT) :])
            continue
        if stripped.startswith("#"):
            pending_comments.append(stripped[1:].strip())
            continue

        parts = stripped.split(None, 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid SSH config line {lineno}: {raw_line}")
        key, value = parts
        comment = " ".join(item for item in pending_comments if item).strip()

        if key == "Host":
            if current is not None:
                hosts.append(current)
            names = value.split()
            if pending_owner is None and len(names) != 1:
                raise ValueError(f"Multi-name Host lacks canonical ownership at line {lineno}")
            # Only the previous single-name format has implicit ownership.
            owner = pending_owner if pending_owner is not None else validate_ssh_name(names[0])
            current = SSHHostConfig(
                server_name=owner,
                host_names=normalize_host_names(owner, names),
                comment=comment or None,
            )
            pending_owner = None
            pending_comments = []
            continue

        if pending_owner is not None:
            raise ValueError(f"Managed ownership must immediately precede Host at line {lineno}")
        if current is None:
            raise ValueError(f"Unexpected SSH config line before Host at line {lineno}: {raw_line}")
        current.add_config(key, value, comment)
        pending_comments = []

    if pending_owner is not None:
        raise ValueError("Managed ownership comment has no Host block")
    if current is not None:
        hosts.append(current)
    validate_managed_hosts(hosts)
    return hosts
