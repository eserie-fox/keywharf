"""Storage helpers for the local checkout of the remote host repository."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from keywharf.config.resolver import ResolvedManagerConfig
from keywharf.storage.json_store import read_json_list, write_json_value


REMOTE_CONFIG_FILENAME = "config.json"


def remote_repo_config_path(config: ResolvedManagerConfig) -> Path:
    return config.ssh_key_local_repo / REMOTE_CONFIG_FILENAME


def load_remote_repo_entries(config: ResolvedManagerConfig) -> list[dict[str, Any]]:
    return read_json_list(remote_repo_config_path(config))


def write_remote_repo_entries(
    config: ResolvedManagerConfig,
    entries: list[dict[str, Any]],
) -> Path:
    return write_json_value(remote_repo_config_path(config), entries)
