"""Runtime resolution for formal manager config."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from ssh_manager.config.models import ManagerConfig
from ssh_manager.runtime.paths import expand_data_root


def _resolve_path(base: Path, value: str | Path, data_root: Path) -> Path:
    expanded = expand_data_root(value, data_root)
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
    data_root: Path
    config_path: Path
    ssh_key_remote_repo: str
    ssh_key_local_repo: Path
    ssh_dir: Path
    managed_config_path: Path
    managed_keys_dir: Path
    state_path: Path

    @property
    def main_config_path(self) -> Path:
        return self.ssh_dir / "config"

    def resolve_from_config_dir(self, value: str | Path) -> Path:
        return _resolve_path(self.config_path.parent, value, self.data_root)

    def resolve_from_local_repo(self, value: str | Path) -> Path:
        return _resolve_path(self.ssh_key_local_repo, value, self.data_root)

    def managed_key_path_for(self, host_name: str, original_identity_file: str) -> Path:
        return self.managed_keys_dir / host_name / Path(original_identity_file).name


def resolve_manager_config(
    raw_config: ManagerConfig,
    *,
    config_path: Path,
    data_root: Path,
) -> ResolvedManagerConfig:
    """Resolve one declarative config into absolute runtime paths."""

    resolved_data_root = data_root.expanduser().resolve()
    resolved_config_path = config_path.expanduser().resolve()
    ssh_key_local_repo = _resolve_path(
        resolved_config_path.parent,
        raw_config.ssh_key_local_repo,
        resolved_data_root,
    )
    ssh_dir = _resolve_path(
        resolved_config_path.parent,
        raw_config.ssh_dir,
        resolved_data_root,
    )
    managed_config_path = (
        _resolve_path(
            resolved_config_path.parent,
            raw_config.managed_config_path,
            resolved_data_root,
        )
        if raw_config.managed_config_path is not None
        else (ssh_dir / "managed" / "ssh-manager.conf").resolve()
    )
    managed_keys_dir = (
        _resolve_path(
            resolved_config_path.parent,
            raw_config.managed_keys_dir,
            resolved_data_root,
        )
        if raw_config.managed_keys_dir is not None
        else (ssh_dir / "managed" / "keys").resolve()
    )
    state_path = _resolve_path(
        resolved_config_path.parent,
        raw_config.state_path,
        resolved_data_root,
    )

    return ResolvedManagerConfig(
        raw=raw_config,
        data_root=resolved_data_root,
        config_path=resolved_config_path,
        ssh_key_remote_repo=raw_config.ssh_key_remote_repo,
        ssh_key_local_repo=ssh_key_local_repo,
        ssh_dir=ssh_dir,
        managed_config_path=managed_config_path,
        managed_keys_dir=managed_keys_dir,
        state_path=state_path,
    )

