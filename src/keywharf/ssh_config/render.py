"""Low-level rendering for SSH config models."""

from __future__ import annotations

from keywharf.domain.models import SSHHostConfig, normalize_host_names
from keywharf.storage.ssh_files import MANAGED_SSH_HEADER

OWNER_COMMENT = "# keywharf-owner: "


def validate_managed_hosts(hosts: list[SSHHostConfig]) -> None:
    owners: set[str] = set()
    names: dict[str, str] = {}
    for host in hosts:
        owner = host.server_name.casefold()
        if owner in owners:
            raise ValueError(f"Duplicate managed ownership for '{host.server_name}'")
        owners.add(owner)
        enabled = normalize_host_names(host.server_name, host.host_names)
        for name in [host.server_name, *enabled]:
            folded = name.casefold()
            if folded in names and names[folded] != owner:
                raise ValueError(f"Ambiguous managed SSH name '{name}'")
            names[folded] = owner


def _indented(indent: int, text: str) -> str:
    return ("\t" * indent) + text


def _render_comment(comment: str | None, indent: int) -> list[str]:
    if not comment:
        return []
    lines = comment.splitlines()
    if any(line.strip().casefold().startswith("keywharf-owner") for line in lines):
        raise ValueError("Human comments cannot use reserved keywharf-owner metadata")
    return [_indented(indent, f"# {line}") for line in lines]


def render_host_config(host: SSHHostConfig, indent: int = 0) -> str:
    names = normalize_host_names(host.server_name, host.host_names)

    lines: list[str] = []
    lines.extend(_render_comment(host.comment, indent))
    lines.append(_indented(indent, f"{OWNER_COMMENT}{host.server_name}"))
    lines.append(_indented(indent, f"Host {' '.join(names)}"))
    lines.extend(_render_comment(host.endpoint.comment, indent + 1))
    if host.endpoint.hostname:
        lines.append(_indented(indent + 1, f"HostName {host.endpoint.hostname}"))
    if host.endpoint.port is not None:
        lines.append(_indented(indent + 1, f"Port {host.endpoint.port}"))
    lines.extend(_render_comment(host.authentication.comment, indent + 1))
    if host.authentication.user:
        lines.append(_indented(indent + 1, f"User {host.authentication.user}"))
    if host.authentication.identity_file:
        lines.append(_indented(indent + 1, f"IdentityFile {host.authentication.identity_file}"))
    for extra in host.extra_config:
        lines.extend(_render_comment(extra.comment, indent + 1))
        if extra.key is None or extra.value is None:
            raise ValueError("SSHExtraConfig requires both key and value")
        lines.append(_indented(indent + 1, f"{extra.key} {extra.value}"))
    return "\n".join(lines) + "\n"


def render_ssh_config(hosts: list[SSHHostConfig]) -> str:
    validate_managed_hosts(hosts)
    lines = [MANAGED_SSH_HEADER]
    for host in sorted(hosts, key=lambda item: item.server_name or ""):
        lines.append("")
        lines.append(render_host_config(host).rstrip())
    lines.append("")
    return "\n".join(lines)
