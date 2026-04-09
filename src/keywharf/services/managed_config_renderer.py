"""Render manager-owned SSH config fragments."""

from __future__ import annotations

from keywharf.domain.models import SSHHostConfig
from keywharf.ssh_config.render import render_ssh_config


def render_managed_config(hosts: list[SSHHostConfig]) -> str:
    return render_ssh_config(hosts)
