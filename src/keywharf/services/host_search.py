"""Host discovery."""

from __future__ import annotations

from collections.abc import Mapping

from keywharf.domain.errors import KeywharfError
from keywharf.domain.models import HostDefinition


def find_host_candidates(host_definitions: Mapping[str, HostDefinition], query: str) -> list[str]:
    normalized = query.strip().casefold()
    if not normalized:
        raise KeywharfError("Host query must not be empty.")

    matches = [
        (rank, server_name)
        for server_name, host in host_definitions.items()
        if (rank := _match_rank(server_name, host, normalized)) is not None
    ]
    if not matches:
        return []
    best_rank = min(rank for rank, _ in matches)
    return sorted(
        (name for rank, name in matches if rank == best_rank),
        key=lambda name: (name.casefold(), name),
    )


def _match_rank(server_name: str, host: HostDefinition, query: str) -> int | None:
    names = [name.casefold() for name in [server_name, *host.aliases]]
    addresses = [endpoint.hostname.casefold() for endpoint in host.endpoints if endpoint.hostname]
    if query in names:
        return 0
    if query in addresses:
        return 1
    fields = [*names, *addresses]
    if any(query in value for value in fields):
        return 2
    return None
