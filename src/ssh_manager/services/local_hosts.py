"""Services for local SSH config host blocks."""

from __future__ import annotations

from ssh_manager.domain.models import ManagerConfig, SSHHostConfig
from ssh_manager.ssh_config.parser import parse_ssh_config
from ssh_manager.ssh_config.render import render_ssh_config
from ssh_manager.storage.ssh_files import read_ssh_config, write_ssh_config


def load_local_hosts(config: ManagerConfig) -> list[SSHHostConfig]:
    content = read_ssh_config(config.ssh_config_path())
    if not content.strip():
        return []
    return sorted(parse_ssh_config(content), key=lambda host: host.name or "")


def render_local_hosts(hosts: list[SSHHostConfig]) -> str:
    return render_ssh_config(hosts)


def write_local_hosts(
    config: ManagerConfig,
    hosts: list[SSHHostConfig],
    *,
    backup: bool = True,
) -> None:
    write_ssh_config(config.ssh_config_path(), render_local_hosts(hosts), backup=backup)
