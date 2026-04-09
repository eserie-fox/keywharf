"""Low-level rendering for SSH config models."""

from __future__ import annotations

from ssh_manager.domain.models import SSHHostConfig
from ssh_manager.storage.ssh_files import MANAGED_SSH_HEADER


def _indented(indent: int, text: str) -> str:
    return f"{'\t' * indent}{text}"


def _render_comment(comment: str | None, indent: int) -> list[str]:
    if not comment:
        return []
    return [_indented(indent, f"# {comment}")]


def render_host_config(host: SSHHostConfig, indent: int = 0) -> str:
    if not host.name:
        raise ValueError("SSHHostConfig name is None")

    lines: list[str] = []
    lines.extend(_render_comment(host.comment, indent))
    lines.append(_indented(indent, f"Host {host.name}"))
    lines.extend(_render_comment(host.endpoint.comment, indent + 1))
    if host.endpoint.hostname:
        lines.append(_indented(indent + 1, f"HostName {host.endpoint.hostname}"))
    if host.endpoint.port is not None:
        lines.append(_indented(indent + 1, f"Port {host.endpoint.port}"))
    lines.extend(_render_comment(host.authentication.comment, indent + 1))
    if host.authentication.user:
        lines.append(_indented(indent + 1, f"User {host.authentication.user}"))
    if host.authentication.identity_file:
        lines.append(
            _indented(indent + 1, f"IdentityFile {host.authentication.identity_file}")
        )
    for extra in host.extra_config:
        lines.extend(_render_comment(extra.comment, indent + 1))
        if extra.key is None or extra.value is None:
            raise ValueError("SSHExtraConfig requires both key and value")
        lines.append(_indented(indent + 1, f"{extra.key} {extra.value}"))
    return "\n".join(lines) + "\n"


def render_ssh_config(hosts: list[SSHHostConfig]) -> str:
    lines = [MANAGED_SSH_HEADER]
    for host in sorted(hosts, key=lambda item: item.name or ""):
        lines.append("")
        lines.append(render_host_config(host).rstrip())
    lines.append("")
    return "\n".join(lines)
