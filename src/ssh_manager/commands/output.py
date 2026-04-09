"""CLI-oriented formatting helpers."""

from __future__ import annotations

import re

from rich.table import Table

from ssh_manager.domain.models import (
    RemoteAuthenticationOption,
    RemoteEndpointOption,
    SSHHostConfig,
)


def compile_pattern(pattern: str | None) -> re.Pattern[str] | None:
    if not pattern:
        return None
    return re.compile(pattern)


def filter_names(items: list[str], pattern: re.Pattern[str] | None) -> list[str]:
    if pattern is None:
        return items
    return [item for item in items if pattern.search(item)]


def filter_hosts(
    hosts: list[SSHHostConfig], pattern: re.Pattern[str] | None
) -> list[SSHHostConfig]:
    if pattern is None:
        return hosts
    return [host for host in hosts if host.name and pattern.search(host.name)]


def summarize_host(host: SSHHostConfig) -> str:
    parts: list[str] = []
    if host.endpoint.hostname:
        if host.endpoint.port is not None:
            parts.append(f"{host.endpoint.hostname}:{host.endpoint.port}")
        else:
            parts.append(host.endpoint.hostname)
    if host.authentication.user:
        parts.append(f"user={host.authentication.user}")
    if host.authentication.identity_file:
        parts.append(f"id={host.authentication.identity_file}")
    return ", ".join(parts) if parts else "-"


def render_endpoint_table(endpoints: list[RemoteEndpointOption]) -> Table:
    table = Table(show_header=True, header_style="bold")
    table.add_column("index", style="cyan", justify="right")
    table.add_column("HostName")
    table.add_column("Port")
    table.add_column("Comment")
    for index, endpoint in enumerate(endpoints):
        table.add_row(
            str(index),
            endpoint.hostname or "",
            str(endpoint.port or ""),
            endpoint.comment or "",
        )
    return table


def render_auth_table(auths: list[RemoteAuthenticationOption]) -> Table:
    table = Table(show_header=True, header_style="bold")
    table.add_column("index", style="cyan", justify="right")
    table.add_column("User")
    table.add_column("IdentityFile")
    table.add_column("Comment")
    for index, auth in enumerate(auths):
        table.add_row(
            str(index),
            auth.user or "",
            auth.identity_file or "",
            auth.comment or "",
        )
    return table
