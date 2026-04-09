"""Services for manager-owned SSH config host blocks."""

from __future__ import annotations

from ssh_manager.domain.models import ManagerConfig, SSHHostConfig
from ssh_manager.ssh_config.parser import parse_ssh_config
from ssh_manager.storage.managed_state import read_managed_config
from ssh_manager.services.apply_managed_config import apply_managed_config
from ssh_manager.services.render_managed_config import render_managed_config


def load_managed_hosts(config: ManagerConfig) -> list[SSHHostConfig]:
    content = read_managed_config(config)
    if not content.strip():
        return []
    return sorted(parse_ssh_config(content), key=lambda host: host.name or "")


def render_managed_hosts(hosts: list[SSHHostConfig]) -> str:
    return render_managed_config(hosts)


def write_managed_hosts(
    config: ManagerConfig,
    hosts: list[SSHHostConfig],
    *,
    backup: bool = True,
) -> None:
    apply_managed_config(config, render_managed_hosts(hosts), backup=backup)


# Compatibility aliases kept for the existing command and facade wiring.
load_local_hosts = load_managed_hosts
render_local_hosts = render_managed_hosts
write_local_hosts = write_managed_hosts
