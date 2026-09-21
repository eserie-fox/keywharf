"""Domain models shared across services and adapters."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

from keywharf.domain.comments import normalize_comment


def _clean_string(value: object | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _clean_int(value: object | None) -> int | None:
    if value is None or value == "":
        return None
    return int(cast(Any, value))


def _normalize_path_string(value: str | Path | None) -> str | None:
    if value is None:
        return None
    return str(value).replace("\\", "/")


STATE_SCHEMA_VERSION = 2


def validate_ssh_name(value: object) -> str:
    """Literal SSH token, also safe as a canonical managed-key directory component."""
    if (
        not isinstance(value, str)
        or re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]*", value) is None
        or value.endswith(".")
        or value.split(".")[0].upper()
        in {
            "CON",
            "PRN",
            "AUX",
            "NUL",
            *(f"COM{i}" for i in range(1, 10)),
            *(f"LPT{i}" for i in range(1, 10)),
        }
    ):
        raise ValueError(f"Invalid literal SSH name: {value!r}")
    return value


def validate_name_list(value: object, *, label: str, nonempty: bool = False) -> list[str]:
    if not isinstance(value, list) or (nonempty and not value):
        raise ValueError(f"{label} must be a {'non-empty ' if nonempty else ''}list of strings")
    names = [validate_ssh_name(item) for item in value]
    if len({name.casefold() for name in names}) != len(names):
        raise ValueError(f"{label} contains duplicate SSH names")
    return names


def normalize_host_names(server_name: str, host_names: object) -> list[str]:
    validate_ssh_name(server_name)
    names = validate_name_list(host_names, label="host_names", nonempty=True)
    return sorted(names, key=lambda name: (name != server_name, name.casefold(), name))


@dataclass(slots=True)
class SelectedHostState:
    server_name: str
    host_names: list[str]
    endpoint_name: str | None = None
    authentication_name: str | None = None

    def __post_init__(self) -> None:
        self.host_names = normalize_host_names(self.server_name, self.host_names)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> SelectedHostState:
        server_name = validate_ssh_name(payload.get("server_name"))
        return cls(
            server_name=server_name,
            host_names=validate_name_list(
                payload.get("host_names"), label="host_names", nonempty=True
            ),
            endpoint_name=_clean_string(payload.get("endpoint_name")),
            authentication_name=_clean_string(payload.get("authentication_name")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "server_name": self.server_name,
            "host_names": normalize_host_names(self.server_name, self.host_names),
            "endpoint_name": self.endpoint_name,
            "authentication_name": self.authentication_name,
        }


@dataclass(slots=True)
class LocalState:
    version: int = STATE_SCHEMA_VERSION
    selected_hosts: list[SelectedHostState] = field(default_factory=list)

    @classmethod
    def empty(cls) -> LocalState:
        return cls()

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> LocalState:
        # Missing version is the explicitly supported legacy-v1 input form.
        version = payload.get("version", 1)
        if type(version) is not int or version not in (1, STATE_SCHEMA_VERSION):
            raise ValueError(f"Unsupported state file version {version!r}")
        selected_hosts_payload = payload.get("selected_hosts", [])
        if not isinstance(selected_hosts_payload, list):
            raise ValueError("selected_hosts must be a list")
        entries: list[SelectedHostState] = []
        for item in selected_hosts_payload:
            if not isinstance(item, dict):
                raise ValueError("selected_hosts entries must be objects")
            if version == 1:
                if "host_names" in item:
                    raise ValueError("v1 state must not contain host_names")
                item = {**item, "host_names": [item.get("server_name")]}
            entries.append(SelectedHostState.from_dict(item))
        names = [item.server_name.casefold() for item in entries]
        if len(set(names)) != len(names):
            raise ValueError("duplicate selection in state")
        return cls(
            version=STATE_SCHEMA_VERSION,
            selected_hosts=entries,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "selected_hosts": [
                item.to_dict()
                for item in sorted(self.selected_hosts, key=lambda current: current.server_name)
            ],
        }

    def get(self, server_name: str) -> SelectedHostState | None:
        for item in self.selected_hosts:
            if item.server_name == server_name:
                return item
        return None

    def upsert(self, selection: SelectedHostState) -> None:
        for index, item in enumerate(self.selected_hosts):
            if item.server_name == selection.server_name:
                self.selected_hosts[index] = selection
                break
        else:
            self.selected_hosts.append(selection)
        self.selected_hosts.sort(key=lambda current: current.server_name)

    def remove(self, server_name: str) -> SelectedHostState | None:
        for index, item in enumerate(self.selected_hosts):
            if item.server_name == server_name:
                return self.selected_hosts.pop(index)
        return None


@dataclass(slots=True)
class HostEndpointOption:
    name: str | None = None
    hostname: str | None = None
    port: int | None = None
    comment: str | None = None

    def __post_init__(self) -> None:
        self.comment = normalize_comment(self.comment)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> HostEndpointOption:
        return cls(
            name=_clean_string(payload.get("EndPointName")),
            hostname=_clean_string(payload.get("HostName")),
            port=_clean_int(payload.get("Port")),
            comment=normalize_comment(payload.get("Comment")),
        )

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if self.name is not None:
            payload["EndPointName"] = self.name
        if self.hostname is not None:
            payload["HostName"] = self.hostname
        if self.port is not None:
            payload["Port"] = self.port
        comment = normalize_comment(self.comment)
        if comment is not None:
            payload["Comment"] = comment
        return payload


@dataclass(slots=True)
class HostAuthenticationOption:
    name: str | None = None
    user: str | None = None
    identity_file: str | None = None
    comment: str | None = None

    def __post_init__(self) -> None:
        self.comment = normalize_comment(self.comment)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> HostAuthenticationOption:
        return cls(
            name=_clean_string(payload.get("AuthenticationName")),
            user=_clean_string(payload.get("User")),
            identity_file=_clean_string(payload.get("IdentityFile")),
            comment=normalize_comment(payload.get("Comment")),
        )

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if self.name is not None:
            payload["AuthenticationName"] = self.name
        if self.user is not None:
            payload["User"] = self.user
        if self.identity_file is not None:
            payload["IdentityFile"] = self.identity_file
        comment = normalize_comment(self.comment)
        if comment is not None:
            payload["Comment"] = comment
        return payload


@dataclass(slots=True)
class HostExtraConfig:
    key: str | None = None
    value: str | None = None
    comment: str | None = None

    def __post_init__(self) -> None:
        self.comment = normalize_comment(self.comment)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> HostExtraConfig:
        return cls(
            key=_clean_string(payload.get("Key")),
            value=_clean_string(payload.get("Value")),
            comment=normalize_comment(payload.get("Comment")),
        )

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if self.key is not None:
            payload["Key"] = self.key
        if self.value is not None:
            payload["Value"] = self.value
        comment = normalize_comment(self.comment)
        if comment is not None:
            payload["Comment"] = comment
        return payload


@dataclass(slots=True)
class HostDefinition:
    server_name: str | None = None
    aliases: list[str] = field(default_factory=list)
    comment: str | None = None
    endpoints: list[HostEndpointOption] = field(default_factory=list)
    authentication: list[HostAuthenticationOption] = field(default_factory=list)
    extra_config: list[HostExtraConfig] = field(default_factory=list)

    def validate_names(self) -> None:
        if self.server_name is not None:
            validate_ssh_name(self.server_name)
        validate_name_list(self.aliases, label="Aliases")
        if self.server_name is not None and any(
            name.casefold() == self.server_name.casefold() for name in self.aliases
        ):
            raise ValueError("Aliases must not repeat ServerName")

    def __post_init__(self) -> None:
        self.validate_names()
        self.comment = normalize_comment(self.comment)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> HostDefinition:
        return cls(
            server_name=payload.get("ServerName"),
            aliases=payload.get("Aliases", []),
            comment=normalize_comment(payload.get("Comment")),
            endpoints=[HostEndpointOption.from_dict(item) for item in payload.get("Endpoint", [])],
            authentication=[
                HostAuthenticationOption.from_dict(item)
                for item in payload.get("Authentication", [])
            ],
            extra_config=[
                HostExtraConfig.from_dict(item) for item in payload.get("ExtraConfig", [])
            ],
        )

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        self.validate_names()
        if self.server_name is not None:
            payload["ServerName"] = self.server_name
        if self.aliases:
            payload["Aliases"] = list(self.aliases)
        comment = normalize_comment(self.comment)
        if comment is not None:
            payload["Comment"] = comment
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

    def __post_init__(self) -> None:
        self.comment = normalize_comment(self.comment)

    def add_comment(self, comment: str) -> None:
        incoming = normalize_comment(comment)
        if incoming is None:
            return
        current = normalize_comment(self.comment)
        self.comment = f"{current}\n{incoming}" if current else incoming

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
            "comment": normalize_comment(self.comment),
        }


@dataclass(slots=True)
class SSHAuthentication:
    user: str | None = None
    identity_file: str | None = None
    source_identity_file: str | None = None
    comment: str | None = None

    def __post_init__(self) -> None:
        self.comment = normalize_comment(self.comment)

    def add_comment(self, comment: str) -> None:
        incoming = normalize_comment(comment)
        if incoming is None:
            return
        current = normalize_comment(self.comment)
        self.comment = f"{current}\n{incoming}" if current else incoming

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
            "comment": normalize_comment(self.comment),
        }


@dataclass(slots=True)
class SSHExtraConfig:
    key: str | None = None
    value: str | None = None
    comment: str | None = None

    def __post_init__(self) -> None:
        self.comment = normalize_comment(self.comment)

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "value": self.value,
            "comment": normalize_comment(self.comment),
        }


@dataclass(slots=True)
class SSHHostConfig:
    server_name: str
    host_names: list[str]
    comment: str | None = None
    endpoint: SSHEndpoint = field(default_factory=SSHEndpoint)
    authentication: SSHAuthentication = field(default_factory=SSHAuthentication)
    extra_config: list[SSHExtraConfig] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.comment = normalize_comment(self.comment)

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
                comment=normalize_comment(comment),
            )
        )

    def get_ssh_identity_file(self) -> str | None:
        return self.authentication.identity_file

    def get_ssh_original_identity_file(self) -> str | None:
        return self.authentication.source_identity_file

    def to_dict(self) -> dict[str, Any]:
        return {
            "server_name": self.server_name,
            "host_names": normalize_host_names(self.server_name, self.host_names),
            "comment": normalize_comment(self.comment),
            "endpoint": self.endpoint.to_dict(),
            "authentication": self.authentication.to_dict(),
            "extra_config": [item.to_dict() for item in self.extra_config],
        }

    def to_string(self, indent: int = 0) -> str:
        from keywharf.ssh_config.render import render_host_config

        return render_host_config(self, indent)
