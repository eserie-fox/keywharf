"""Result objects shared across services and CLI adapters."""

from __future__ import annotations

from dataclasses import dataclass, field

from ssh_manager.domain.models import SSHHostConfig


@dataclass(slots=True)
class ValidationResult:
    ok: bool
    errors: list[str] = field(default_factory=list)


@dataclass(slots=True)
class HostMutationResult:
    host: SSHHostConfig
    hosts: list[SSHHostConfig]
