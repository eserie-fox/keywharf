"""Domain models shared across services and adapters."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


def _clean_string(value: object | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _clean_int(value: object | None) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


def _normalize_path_string(value: str | Path | None) -> str | None:
    if value is None:
        return None
    return str(value).replace("\\", "/")


def _resolve_path(base: Path, value: str | Path, data_root: Path) -> Path:
    text = str(value).replace("%{DATA_ROOT}", str(data_root))
    text = os.path.expandvars(os.path.expanduser(text))
    candidate = Path(text)
    if not candidate.is_absolute():
        candidate = (base / candidate).resolve()
    else:
        candidate = candidate.resolve()
    return candidate


@dataclass(slots=True)
class ManagerConfig:
    data_root: Path
    config_path: Path
    ssh_key_remote_repo: str
    ssh_key_local_repo: Path
    ssh_dir: Path
    raw: dict[str, Any] = field(default_factory=dict)

    def ssh_config_path(self) -> Path:
        return self.ssh_dir / "config"

    def resolve_from_config_dir(self, value: str | Path) -> Path:
        return _resolve_path(self.config_path.parent, value, self.data_root)

    def resolve_from_local_repo(self, value: str | Path) -> Path:
        return _resolve_path(self.ssh_key_local_repo, value, self.data_root)

    def data(self) -> dict[str, Any]:
        return {
            **self.raw,
            "ssh_key_remote_repo": self.ssh_key_remote_repo,
            "ssh_key_local_repo": self.ssh_key_local_repo.as_posix(),
            "ssh_dir": self.ssh_dir.as_posix(),
        }


@dataclass(slots=True)
class RemoteEndpointOption:
    name: str | None = None
    hostname: str | None = None
    port: int | None = None
    comment: str | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "RemoteEndpointOption":
        return cls(
            name=_clean_string(payload.get("EndPointName")),
            hostname=_clean_string(payload.get("HostName")),
            port=_clean_int(payload.get("Port")),
            comment=_clean_string(payload.get("Comment")),
        )

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if self.name is not None:
            payload["EndPointName"] = self.name
        if self.hostname is not None:
            payload["HostName"] = self.hostname
        if self.port is not None:
            payload["Port"] = self.port
        if self.comment is not None:
            payload["Comment"] = self.comment
        return payload


@dataclass(slots=True)
class RemoteAuthenticationOption:
    name: str | None = None
    user: str | None = None
    identity_file: str | None = None
    comment: str | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "RemoteAuthenticationOption":
        return cls(
            name=_clean_string(payload.get("AuthenticationName")),
            user=_clean_string(payload.get("User")),
            identity_file=_clean_string(payload.get("IdentityFile")),
            comment=_clean_string(payload.get("Comment")),
        )

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if self.name is not None:
            payload["AuthenticationName"] = self.name
        if self.user is not None:
            payload["User"] = self.user
        if self.identity_file is not None:
            payload["IdentityFile"] = self.identity_file
        if self.comment is not None:
            payload["Comment"] = self.comment
        return payload


@dataclass(slots=True)
class RemoteExtraConfig:
    key: str | None = None
    value: str | None = None
    comment: str | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "RemoteExtraConfig":
        return cls(
            key=_clean_string(payload.get("Key")),
            value=_clean_string(payload.get("Value")),
            comment=_clean_string(payload.get("Comment")),
        )

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if self.key is not None:
            payload["Key"] = self.key
        if self.value is not None:
            payload["Value"] = self.value
        if self.comment is not None:
            payload["Comment"] = self.comment
        return payload


@dataclass(slots=True)
class RemoteHostDefinition:
    server_name: str | None = None
    comment: str | None = None
    endpoints: list[RemoteEndpointOption] = field(default_factory=list)
    authentication: list[RemoteAuthenticationOption] = field(default_factory=list)
    extra_config: list[RemoteExtraConfig] = field(default_factory=list)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "RemoteHostDefinition":
        return cls(
            server_name=_clean_string(payload.get("ServerName")),
            comment=_clean_string(payload.get("Comment")),
            endpoints=[
                RemoteEndpointOption.from_dict(item)
                for item in payload.get("Endpoint", [])
            ],
            authentication=[
                RemoteAuthenticationOption.from_dict(item)
                for item in payload.get("Authentication", [])
            ],
            extra_config=[
                RemoteExtraConfig.from_dict(item)
                for item in payload.get("ExtraConfig", [])
            ],
        )

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if self.server_name is not None:
            payload["ServerName"] = self.server_name
        if self.comment is not None:
            payload["Comment"] = self.comment
        if self.endpoints:
            payload["Endpoint"] = [item.to_dict() for item in self.endpoints]
        if self.authentication:
            payload["Authentication"] = [item.to_dict() for item in self.authentication]
        if self.extra_config:
            payload["ExtraConfig"] = [item.to_dict() for item in self.extra_config]
        return payload


@dataclass(slots=True)
class SSHEndpoint:
    hostname: str | None = None
    port: int | None = None
    comment: str | None = None

    def add_comment(self, comment: str) -> None:
        comment = comment.strip()
        if not comment:
            return
        self.comment = f"{self.comment} {comment}".strip() if self.comment else comment

    def add_config(self, key: str, value: str, comment: str) -> bool:
        if key == "HostName":
            self.hostname = _clean_string(value)
        elif key == "Port":
            self.port = _clean_int(value)
        else:
            return False
        self.add_comment(comment)
        return True

    def to_dict(self) -> dict[str, Any]:
        return {
            "hostname": self.hostname,
            "port": self.port,
            "comment": self.comment,
        }


@dataclass(slots=True)
class SSHAuthentication:
    user: str | None = None
    identity_file: str | None = None
    source_identity_file: str | None = None
    comment: str | None = None

    def add_comment(self, comment: str) -> None:
        comment = comment.strip()
        if not comment:
            return
        self.comment = f"{self.comment} {comment}".strip() if self.comment else comment

    def add_config(self, key: str, value: str, comment: str) -> bool:
        if key == "User":
            self.user = _clean_string(value)
        elif key == "IdentityFile":
            self.identity_file = _normalize_path_string(value)
            self.source_identity_file = None
        else:
            return False
        self.add_comment(comment)
        return True

    def to_dict(self) -> dict[str, Any]:
        return {
            "user": self.user,
            "identity_file": self.identity_file,
            "comment": self.comment,
        }


@dataclass(slots=True)
class SSHExtraConfig:
    key: str | None = None
    value: str | None = None
    comment: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "value": self.value,
            "comment": self.comment,
        }


@dataclass(slots=True)
class SSHHostConfig:
    name: str | None = None
    comment: str | None = None
    endpoint: SSHEndpoint = field(default_factory=SSHEndpoint)
    authentication: SSHAuthentication = field(default_factory=SSHAuthentication)
    extra_config: list[SSHExtraConfig] = field(default_factory=list)

    def add_config(self, key: str, value: str, comment: str) -> None:
        stripped_value = value.strip("'\"")
        if self.endpoint.add_config(key, stripped_value, comment):
            return
        if self.authentication.add_config(key, stripped_value, comment):
            return
        self.extra_config.append(
            SSHExtraConfig(
                key=_clean_string(key),
                value=_clean_string(stripped_value),
                comment=_clean_string(comment),
            )
        )

    def get_ssh_identity_file(self) -> str | None:
        return self.authentication.identity_file

    def get_ssh_original_identity_file(self) -> str | None:
        return self.authentication.source_identity_file

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "comment": self.comment,
            "endpoint": self.endpoint.to_dict(),
            "authentication": self.authentication.to_dict(),
            "extra_config": [item.to_dict() for item in self.extra_config],
        }

    def to_string(self, indent: int = 0) -> str:
        from ssh_manager.ssh_config.render import render_host_config

        return render_host_config(self, indent)
