"""JSON storage helpers."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from keywharf.domain.errors import KeywharfError


def read_json_value(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def read_json_object(path: Path) -> dict[str, Any]:
    payload = read_json_value(path)
    if not isinstance(payload, dict):
        raise KeywharfError(f"Expected JSON object in {path}", exit_code=2)
    return payload


def read_json_list(path: Path) -> list[dict[str, Any]]:
    payload = read_json_value(path)
    if not isinstance(payload, list):
        raise KeywharfError(f"Expected JSON list in {path}", exit_code=1)
    return payload


def write_json_value(path: Path, payload: Any) -> Path:
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
    return path
