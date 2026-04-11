"""Runtime resolution for formal manager config."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from keywharf.config.models import ManagerConfig
from keywharf.runtime.paths import expand_workspace_root


def _resolve_path(base: Path, value: str | Path, workspace_root: Path) -> Path:
    expanded = expand_workspace_root(value, workspace_root)
    text = os.path.expandvars(os.path.expanduser(str(expanded)))
    candidate = Path(text)
    if not candidate.is_absolute():
        candidate = (base / candidate).resolve()
    else:
        candidate = candidate.resolve()
    return candidate


@dataclass(slots=True)
class ResolvedManagerConfig:
    """Apply-ready manager config with fully resolved paths."""

    raw: ManagerConfig
    workspace_root: Path
    config_path: Path
    host_repo_remote_url: str | None
    host_repo_path: Path
    ssh_dir: Path
    managed_config_path: Path
    managed_keys_dir: Path
    state_path: Path

    @property
    def main_config_path(self) -> Path:
        return self.ssh_dir / "config"

    def resolve_from_config_dir(self, value: str | Path) -> Path:
        return _resolve_path(self.config_path.parent, value, self.workspace_root)

    def resolve_from_host_repo(self, value: str | Path) -> Path:
        return _resolve_path(self.host_repo_path, value, self.workspace_root)

    def managed_key_path_for(self, host_name: str, original_identity_file: str) -> Path:
        return self.managed_keys_dir / host_name / Path(original_identity_file).name


def resolve_manager_config(
    raw_config: ManagerConfig,
    *,
    config_path: Path,
    workspace_root: Path,
) -> ResolvedManagerConfig:
    """Resolve one declarative config into absolute runtime paths."""

    resolved_workspace_root = workspace_root.expanduser().resolve()
    resolved_config_path = config_path.expanduser().resolve()
    host_repo_path = _resolve_path(
        resolved_config_path.parent,
        raw_config.host_repo_path,
        resolved_workspace_root,
    )
    ssh_dir = _resolve_path(
        resolved_config_path.parent,
        raw_config.ssh_dir,
        resolved_workspace_root,
    )
    managed_config_path = (
        _resolve_path(
            resolved_config_path.parent,
            raw_config.managed_config_path,
            resolved_workspace_root,
        )
        if raw_config.managed_config_path is not None
        else (ssh_dir / "managed" / "keywharf.conf").resolve()
    )
    managed_keys_dir = (
        _resolve_path(
            resolved_config_path.parent,
            raw_config.managed_keys_dir,
            resolved_workspace_root,
        )
        if raw_config.managed_keys_dir is not None
        else (ssh_dir / "managed" / "keys").resolve()
    )
    state_path = _resolve_path(
        resolved_config_path.parent,
        raw_config.state_path,
        resolved_workspace_root,
    )

    return ResolvedManagerConfig(
        raw=raw_config,
        workspace_root=resolved_workspace_root,
        config_path=resolved_config_path,
        host_repo_remote_url=raw_config.host_repo_remote_url,
        host_repo_path=host_repo_path,
        ssh_dir=ssh_dir,
        managed_config_path=managed_config_path,
        managed_keys_dir=managed_keys_dir,
        state_path=state_path,
    )
