"""Result objects shared across services and CLI adapters."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from keywharf.domain.models import (
    HostAuthenticationOption,
    HostDefinition,
    HostEndpointOption,
    SSHHostConfig,
    SelectedHostState,
)


@dataclass(slots=True)
class ValidationResult:
    ok: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
        }


@dataclass(slots=True)
class HostMutationResult:
    host: SSHHostConfig
    hosts: list[SSHHostConfig]


@dataclass(slots=True)
class HostRepoMutationResult:
    operation: str
    subject: str
    config_path: Path
    name: str
    server_name: str | None = None
    host: HostDefinition | None = None
    endpoint: HostEndpointOption | None = None
    auth: HostAuthenticationOption | None = None
    notes: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    changed: bool = True

    def to_dict(self) -> dict[str, object]:
        return {
            "operation": self.operation,
            "subject": self.subject,
            "config_path": self.config_path.as_posix(),
            "name": self.name,
            "server_name": self.server_name,
            "host": self.host.to_dict() if self.host is not None else None,
            "endpoint": self.endpoint.to_dict() if self.endpoint is not None else None,
            "auth": self.auth.to_dict() if self.auth is not None else None,
            "notes": list(self.notes),
            "warnings": list(self.warnings),
            "changed": self.changed,
        }


@dataclass(slots=True)
class IncludeInstallResult:
    main_config_path: Path
    managed_config_path: Path
    include_line: str
    already_present: bool
    changed: bool
    dry_run: bool
    rendered_content: str


@dataclass(slots=True)
class ManagedKeyCopyPlan:
    source: Path
    target: Path

    def to_dict(self) -> dict[str, str]:
        return {
            "source": self.source.as_posix(),
            "target": self.target.as_posix(),
        }


@dataclass(slots=True)
class ResolvedHostSelection:
    selection: SelectedHostState
    host_definition: HostDefinition
    endpoint: HostEndpointOption
    authentication: HostAuthenticationOption
    endpoint_index: int
    authentication_index: int

    def to_dict(self) -> dict[str, object]:
        return {
            "selection": self.selection.to_dict(),
            "host_definition": self.host_definition.to_dict(),
            "endpoint": self.endpoint.to_dict(),
            "authentication": self.authentication.to_dict(),
            "endpoint_index": self.endpoint_index,
            "authentication_index": self.authentication_index,
        }


@dataclass(slots=True)
class RenderResult:
    content: str
    resolved_hosts: list[SSHHostConfig] = field(default_factory=list)
    resolved_selections: list[ResolvedHostSelection] = field(default_factory=list)
    planned_key_copies: list[ManagedKeyCopyPlan] = field(default_factory=list)
    planned_key_deletes: list[Path] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    orphaned_hosts: list[str] = field(default_factory=list)
    in_sync: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "content": self.content,
            "resolved_hosts": [item.to_dict() for item in self.resolved_hosts],
            "resolved_selections": [item.to_dict() for item in self.resolved_selections],
            "planned_key_copies": [item.to_dict() for item in self.planned_key_copies],
            "planned_key_deletes": [item.as_posix() for item in self.planned_key_deletes],
            "warnings": list(self.warnings),
            "orphaned_hosts": list(self.orphaned_hosts),
            "in_sync": self.in_sync,
        }


@dataclass(slots=True)
class ApplyResult:
    managed_config_path: Path
    render_result: RenderResult
    copied_keys: list[Path] = field(default_factory=list)
    deleted_keys: list[Path] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    changed: bool = False
    dry_run: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "managed_config_path": self.managed_config_path.as_posix(),
            "render_result": self.render_result.to_dict(),
            "copied_keys": [item.as_posix() for item in self.copied_keys],
            "deleted_keys": [item.as_posix() for item in self.deleted_keys],
            "warnings": list(self.warnings),
            "changed": self.changed,
            "dry_run": self.dry_run,
        }


@dataclass(slots=True)
class LocalHostStatus:
    server_name: str
    status: str
    selection: SelectedHostState | None = None
    desired_host: SSHHostConfig | None = None
    current_host: SSHHostConfig | None = None
    resolved_selection: ResolvedHostSelection | None = None
    reason: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "server_name": self.server_name,
            "status": self.status,
            "selection": self.selection.to_dict() if self.selection is not None else None,
            "desired_host": self.desired_host.to_dict() if self.desired_host is not None else None,
            "current_host": self.current_host.to_dict() if self.current_host is not None else None,
            "resolved_selection": (
                self.resolved_selection.to_dict()
                if self.resolved_selection is not None
                else None
            ),
            "reason": self.reason,
        }


@dataclass(slots=True)
class InitResult:
    workspace_root: Path
    config_path: Path
    state_path: Path
    host_repo_path: Path
    created_paths: list[Path] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "workspace_root": self.workspace_root.as_posix(),
            "config_path": self.config_path.as_posix(),
            "state_path": self.state_path.as_posix(),
            "host_repo_path": self.host_repo_path.as_posix(),
            "created_paths": [item.as_posix() for item in self.created_paths],
        }


@dataclass(slots=True)
class HostRepoInitResult:
    host_repo_path: Path
    config_path: Path
    created_paths: list[Path] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "host_repo_path": self.host_repo_path.as_posix(),
            "config_path": self.config_path.as_posix(),
            "created_paths": [item.as_posix() for item in self.created_paths],
        }
