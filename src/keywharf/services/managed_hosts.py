"""Services for manager-owned SSH config host blocks."""

from __future__ import annotations

from keywharf.config.resolver import ResolvedManagerConfig
from keywharf.domain.models import SSHHostConfig
from keywharf.services.managed_config_applier import apply_managed_config
from keywharf.services.managed_config_renderer import render_managed_config
from keywharf.ssh_config.parser import parse_ssh_config
from keywharf.storage.managed_files import read_managed_config


def load_managed_hosts(config: ResolvedManagerConfig) -> list[SSHHostConfig]:
    content = read_managed_config(config)
    if not content.strip():
        return []
    return sorted(parse_ssh_config(content), key=lambda host: host.name or "")


def render_managed_hosts(hosts: list[SSHHostConfig]) -> str:
    return render_managed_config(hosts)


def write_managed_hosts(
    config: ResolvedManagerConfig,
    hosts: list[SSHHostConfig],
    *,
    backup: bool = True,
) -> None:
    apply_managed_config(config, render_managed_hosts(hosts), backup=backup)

