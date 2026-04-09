"""Pydantic manager-config schema."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from pydantic import BaseModel, ConfigDict, field_validator

from keywharf.config.merge import config_deep_merge
from keywharf.config.resources import read_json_mapping


_MANAGER_DEFAULTS_RESOURCE_SPEC = "pkg://keywharf/config_defaults/manager.json"


class ManagerConfig(BaseModel):
    """Declarative, unresolved manager config."""

    model_config = ConfigDict(extra="forbid")

    ssh_key_remote_repo: str
    ssh_key_local_repo: str
    ssh_dir: str
    managed_config_path: str | None
    managed_keys_dir: str | None
    state_path: str

    @field_validator(
        "ssh_key_remote_repo",
        "ssh_key_local_repo",
        "ssh_dir",
        "state_path",
    )
    @classmethod
    def _validate_required_strings(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("value must not be blank")
        return text

    @field_validator("managed_config_path", "managed_keys_dir")
    @classmethod
    def _validate_optional_strings(cls, value: str | None) -> str | None:
        if value is None:
            return None
        text = value.strip()
        if not text:
            raise ValueError("value must not be blank")
        return text

    @classmethod
    def from_defaults(cls) -> "ManagerConfig":
        return cls.model_validate(read_json_mapping(_MANAGER_DEFAULTS_RESOURCE_SPEC))

    @classmethod
    def from_file(cls, path: str | Path) -> "ManagerConfig":
        override = read_json_mapping(Path(path).expanduser())
        defaults = read_json_mapping(_MANAGER_DEFAULTS_RESOURCE_SPEC)
        return cls.model_validate(config_deep_merge(defaults, override))

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "ManagerConfig":
        defaults = read_json_mapping(_MANAGER_DEFAULTS_RESOURCE_SPEC)
        return cls.model_validate(config_deep_merge(defaults, dict(data)))
