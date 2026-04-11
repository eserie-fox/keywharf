"""Storage helpers for the workspace host repo."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from keywharf.config.resolver import ResolvedManagerConfig
from keywharf.storage.json_store import read_json_list, write_json_value


HOST_REPO_CONFIG_FILENAME = "config.json"


def host_repo_config_path(config: ResolvedManagerConfig) -> Path:
    return config.host_repo_path / HOST_REPO_CONFIG_FILENAME


def load_host_repo_entries(config: ResolvedManagerConfig) -> list[dict[str, Any]]:
    return read_json_list(host_repo_config_path(config))


def write_host_repo_entries(
    config: ResolvedManagerConfig,
    entries: list[dict[str, Any]],
) -> Path:
    return write_json_value(host_repo_config_path(config), entries)
