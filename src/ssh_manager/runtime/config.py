"""Runtime configuration loading and path normalization."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Mapping

from ssh_manager.domain.models import ManagerConfig
from ssh_manager.runtime.paths import expand_data_root, resolve_data_root
from ssh_manager.storage.json_store import read_json_object


def _normalize_path(base: Path, value: str | Path, data_root: Path) -> Path:
    expanded = expand_data_root(value, data_root)
    text = os.path.expandvars(os.path.expanduser(str(expanded)))
    candidate = Path(text)
    if not candidate.is_absolute():
        candidate = (base / candidate).resolve()
    else:
        candidate = candidate.resolve()
    return candidate


def default_manager_config_payload(
    *,
    ssh_key_remote_repo: str = "git@example.com:org/keys.git",
    ssh_dir: str = "~/.ssh",
) -> dict[str, str]:
    return {
        "ssh_key_remote_repo": ssh_key_remote_repo,
        "ssh_key_local_repo": "%{DATA_ROOT}/repos/keys",
        "ssh_dir": ssh_dir,
        "managed_config_path": f"{ssh_dir}/managed/ssh-manager.conf",
        "managed_keys_dir": f"{ssh_dir}/managed/keys",
        "state_path": "%{DATA_ROOT}/state/state.json",
    }


def resolve_config_path(
    config_override: Path | None = None,
    *,
    data_root: Path | None = None,
    cwd: Path | None = None,
    home: Path | None = None,
    env: Mapping[str, str] | None = None,
) -> Path:
    """Resolve the manager config path from CLI input and runtime context."""

    if config_override is None:
        resolved_data_root = data_root or resolve_data_root(cwd=cwd, home=home, env=env)
        return (resolved_data_root / "config.json").resolve()

    raw_candidate = Path(config_override).expanduser()
    if raw_candidate.is_absolute() and data_root is None:
        return raw_candidate.resolve()

    resolved_data_root = data_root
    if resolved_data_root is None:
        resolved_data_root = resolve_data_root(cwd=cwd, home=home, env=env)

    expanded = expand_data_root(config_override, resolved_data_root)
    candidate = Path(str(expanded)).expanduser()
    if not candidate.is_absolute():
        candidate = (resolved_data_root / candidate).resolve()
    else:
        candidate = candidate.resolve()
    return candidate


def load_manager_config(
    config_override: Path | None = None,
    *,
    data_root: Path | None = None,
    cwd: Path | None = None,
    home: Path | None = None,
    env: Mapping[str, str] | None = None,
) -> ManagerConfig:
    """Load the manager config with paths fully resolved."""

    absolute_override = None
    if config_override is not None:
        candidate = Path(config_override).expanduser()
        if candidate.is_absolute():
            absolute_override = candidate.resolve()

    if data_root is not None:
        resolved_data_root = data_root
    elif absolute_override is not None:
        resolved_data_root = absolute_override.parent
    else:
        resolved_data_root = resolve_data_root(cwd=cwd, home=home, env=env)

    config_path = resolve_config_path(
        config_override,
        data_root=resolved_data_root,
        cwd=cwd,
        home=home,
        env=env,
    )
    payload = read_json_object(config_path)

    ssh_key_local_repo = _normalize_path(
        config_path.parent, payload["ssh_key_local_repo"], resolved_data_root
    )
    ssh_dir = _normalize_path(config_path.parent, payload["ssh_dir"], resolved_data_root)
    managed_config_path = (
        _normalize_path(config_path.parent, payload["managed_config_path"], resolved_data_root)
        if "managed_config_path" in payload
        else (ssh_dir / "managed" / "ssh-manager.conf").resolve()
    )
    managed_keys_dir = (
        _normalize_path(config_path.parent, payload["managed_keys_dir"], resolved_data_root)
        if "managed_keys_dir" in payload
        else (ssh_dir / "managed" / "keys").resolve()
    )
    state_path = (
        _normalize_path(config_path.parent, payload["state_path"], resolved_data_root)
        if "state_path" in payload
        else (resolved_data_root / "state" / "state.json").resolve()
    )

    return ManagerConfig(
        data_root=resolved_data_root,
        config_path=config_path,
        ssh_key_remote_repo=str(payload["ssh_key_remote_repo"]),
        ssh_key_local_repo=ssh_key_local_repo,
        ssh_dir=ssh_dir,
        managed_config_path=managed_config_path,
        managed_keys_dir=managed_keys_dir,
        state_path=state_path,
        raw=dict(payload),
    )


class Config:
    """Thin compatibility wrapper around the new manager config model."""

    def __init__(self, config_file_path: str | Path | None = None) -> None:
        override = Path(config_file_path).expanduser() if config_file_path is not None else None
        self._model = load_manager_config(override)
        self.config_path = self._model.config_path
        self.config_abs_path = self.config_path.parent
        self.local_repo_abs_path = self._model.ssh_key_local_repo.as_posix()

    def to_abs_path_based_on_config(self, relevant_path: str) -> str:
        return self._model.resolve_from_config_dir(relevant_path).as_posix()

    def to_abs_path_based_on_local_repo(self, relevant_path: str) -> str:
        return self._model.resolve_from_local_repo(relevant_path).as_posix()

    def data(self) -> dict[str, Any]:
        return self._model.data()

    @property
    def model(self) -> ManagerConfig:
        return self._model
