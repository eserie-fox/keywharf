"""JSON storage helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ssh_manager.domain.errors import SSHManagerError


def read_json_value(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def read_json_object(path: Path) -> dict[str, Any]:
    payload = read_json_value(path)
    if not isinstance(payload, dict):
        raise SSHManagerError(f"Expected JSON object in {path}", exit_code=2)
    return payload


def read_json_list(path: Path) -> list[dict[str, Any]]:
    payload = read_json_value(path)
    if not isinstance(payload, list):
        raise SSHManagerError(f"Expected JSON list in {path}", exit_code=1)
    return payload
