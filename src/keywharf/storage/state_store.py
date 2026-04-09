"""Storage helpers for the explicit local desired-state file."""

from __future__ import annotations

import json
import os
from pathlib import Path

from keywharf.config.resolver import ResolvedManagerConfig
from keywharf.domain.errors import KeywharfError
from keywharf.domain.models import LocalState, STATE_SCHEMA_VERSION
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

    if state.version != STATE_SCHEMA_VERSION:
        raise KeywharfError(
            f"Unsupported state file version {state.version} at {path}. "
            f"Expected {STATE_SCHEMA_VERSION}.",
        )

    seen: set[str] = set()
    for item in state.selected_hosts:
        if item.server_name in seen:
            raise KeywharfError(
                f"Invalid state file at {path}: duplicate selection for '{item.server_name}'."
            )
        seen.add(item.server_name)

    state.selected_hosts.sort(key=lambda current: current.server_name)
    return state


def save_state(config: ResolvedManagerConfig, state: LocalState) -> None:
    path = config.state_path
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f"{path.name}.tmp")

    with tmp_path.open("w", encoding="utf-8") as handle:
        json.dump(state.to_dict(), handle, indent=2)
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
