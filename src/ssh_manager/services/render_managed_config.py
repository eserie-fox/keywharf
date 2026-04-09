"""Render manager-owned SSH config fragments."""

from __future__ import annotations

from ssh_manager.domain.models import SSHHostConfig
from ssh_manager.ssh_config.render import render_ssh_config


def render_managed_config(hosts: list[SSHHostConfig]) -> str:
    return render_ssh_config(hosts)
