"""Storage helpers for the explicit local desired-state file."""

from __future__ import annotations

import json
import os
from pathlib import Path

from keywharf.config.resolver import ResolvedManagerConfig
from keywharf.domain.errors import KeywharfError
from keywharf.domain.models import STATE_SCHEMA_VERSION, LocalState
from keywharf.storage.json_store import read_json_object


def empty_state() -> LocalState:
    return LocalState.empty()


def state_exists(config: ResolvedManagerConfig) -> bool:
    return config.state_path.exists()


def load_state(config: ResolvedManagerConfig, *, allow_missing: bool = True) -> LocalState:
    path = config.state_path
    if not path.exists():
        if allow_missing:
            return empty_state()
        raise FileNotFoundError(path)

    payload = read_json_object(path)
    try:
        state = LocalState.from_dict(payload)
    except ValueError as exc:
        raise KeywharfError(f"Invalid state file at {path}: {exc}") from exc

    state.selected_hosts.sort(key=lambda current: current.server_name)
    return state


def save_state(config: ResolvedManagerConfig, state: LocalState) -> None:
    try:
        if state.version != STATE_SCHEMA_VERSION:
            raise ValueError("Only v2 state may be saved")
        payload = LocalState.from_dict(state.to_dict()).to_dict()
    except ValueError as exc:
        raise KeywharfError(f"Invalid state: {exc}") from exc
    path = config.state_path
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f"{path.name}.tmp")

    with tmp_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())

    try:
        os.replace(tmp_path, path)
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink()
        raise


def ensure_state_file(config: ResolvedManagerConfig) -> Path:
    if not config.state_path.exists():
        save_state(config, empty_state())
    return config.state_path
