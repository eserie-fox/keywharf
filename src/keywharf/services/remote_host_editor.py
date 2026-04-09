"""Structured editing of remote host definitions in the local repo checkout."""

from __future__ import annotations

from copy import deepcopy

from keywharf.config.resolver import ResolvedManagerConfig
from keywharf.domain.errors import KeywharfError
from keywharf.domain.models import (
    RemoteAuthenticationOption,
    RemoteEndpointOption,
    RemoteHostDefinition,
)
from keywharf.domain.results import RemoteHostMutationResult
from keywharf.services.privilege import can_read_path, can_write_file, root_owned_hint
from keywharf.services.remote_hosts import load_remote_host_list, validate_remote_host_definitions
from keywharf.storage.remote_repo import remote_repo_config_path, write_remote_repo_entries
from keywharf.storage.state_store import load_state


def list_remote_hosts(config: ResolvedManagerConfig) -> list[RemoteHostDefinition]:
    return _load_hosts_or_raise(config)


def get_remote_host(config: ResolvedManagerConfig, server_name: str) -> RemoteHostDefinition:
    for host in _load_hosts_or_raise(config):
        if host.server_name == server_name:
            return host
    raise KeywharfError(f"Remote host '{server_name}' not found.")


def add_remote_host(
    config: ResolvedManagerConfig,
    *,
    server_name: str,
    hostname: str,
    user: str,
    identity_file: str,
    port: int = 22,
    comment: str | None = None,
    endpoint_name: str | None = None,
    auth_name: str | None = None,
) -> RemoteHostMutationResult:
    hosts = _load_hosts_or_raise(config)
    if any(host.server_name == server_name for host in hosts):
        raise KeywharfError(f"Remote host '{server_name}' already exists.")

    new_host = RemoteHostDefinition(
        server_name=_clean_required(server_name, label="server name"),
        comment=_clean_optional(comment),
        endpoints=[
            RemoteEndpointOption(
                name=_clean_optional(endpoint_name),
                hostname=_clean_required(hostname, label="hostname"),
                port=port,
            )
        ],
        authentication=[
            RemoteAuthenticationOption(
                name=_clean_optional(auth_name),
                user=_clean_required(user, label="user"),
                identity_file=_clean_required(identity_file, label="identity file"),
            )
        ],
    )
    updated_hosts = [*hosts, new_host]
    _persist_remote_hosts(config, updated_hosts)
    return RemoteHostMutationResult(
        operation="add",
        config_path=remote_repo_config_path(config),
        host=new_host,
    )


def update_remote_host(
    config: ResolvedManagerConfig,
    *,
    server_name: str,
    new_name: str | None = None,
    comment: str | None = None,
    hostname: str | None = None,
    port: int | None = None,
    user: str | None = None,
    identity_file: str | None = None,
    endpoint_name: str | None = None,
    auth_name: str | None = None,
    target_endpoint: str | None = None,
    target_auth: str | None = None,
) -> RemoteHostMutationResult:
    hosts = _load_hosts_or_raise(config)
    index, current = _find_host_index(hosts, server_name)
    updated = deepcopy(current)

    old_server_name = current.server_name
    old_endpoint_name: str | None = None
    new_endpoint_resolved_name: str | None = None
    old_auth_name: str | None = None
    new_auth_resolved_name: str | None = None

    if new_name is not None:
        updated.server_name = _clean_required(new_name, label="new server name")
    if comment is not None:
        updated.comment = _clean_optional(comment)

    if any(value is not None for value in (hostname, port, endpoint_name)):
        endpoint_index = _resolve_target_endpoint(updated, server_name, target_endpoint)
        endpoint = updated.endpoints[endpoint_index]
        old_endpoint_name = current.endpoints[endpoint_index].name
        if endpoint_name is not None:
            endpoint.name = _clean_optional(endpoint_name)
        if hostname is not None:
            endpoint.hostname = _clean_required(hostname, label="hostname")
        if port is not None:
            endpoint.port = port
        new_endpoint_resolved_name = endpoint.name

    if any(value is not None for value in (user, identity_file, auth_name)):
        auth_index = _resolve_target_auth(updated, server_name, target_auth)
        auth = updated.authentication[auth_index]
        old_auth_name = current.authentication[auth_index].name
        if auth_name is not None:
            auth.name = _clean_optional(auth_name)
        if user is not None:
            auth.user = _clean_required(user, label="user")
        if identity_file is not None:
            auth.identity_file = _clean_required(identity_file, label="identity file")
        new_auth_resolved_name = auth.name

    if updated.to_dict() == current.to_dict():
        return RemoteHostMutationResult(
            operation="update",
            config_path=remote_repo_config_path(config),
            host=current,
            changed=False,
        )

    hosts[index] = updated
    _persist_remote_hosts(config, hosts)
    return RemoteHostMutationResult(
        operation="update",
        config_path=remote_repo_config_path(config),
        host=updated,
        warnings=_selection_warnings(
            config,
            old_server_name=old_server_name,
            new_server_name=updated.server_name,
            old_endpoint_name=old_endpoint_name,
            new_endpoint_name=new_endpoint_resolved_name,
            old_auth_name=old_auth_name,
            new_auth_name=new_auth_resolved_name,
        ),
    )


def remove_remote_host(
    config: ResolvedManagerConfig,
    *,
    server_name: str,
) -> RemoteHostMutationResult:
    hosts = _load_hosts_or_raise(config)
    index, removed = _find_host_index(hosts, server_name)
    del hosts[index]
    _persist_remote_hosts(config, hosts)
    return RemoteHostMutationResult(
        operation="remove",
        config_path=remote_repo_config_path(config),
        host=removed,
        removed_name=server_name,
        warnings=_selection_warnings(config, removed_server_name=server_name),
    )


def analyze_remote_host_write_root_requirements(config: ResolvedManagerConfig) -> list[str]:
    """Return concrete privilege reasons for mutating the local remote config."""

    config_path = remote_repo_config_path(config)
    reasons: list[str] = []
    if config_path.exists() and not can_read_path(config_path):
        reasons.append(
            f"remote repository config is not readable by current user: {config_path}{root_owned_hint(config_path)}"
        )
    if not can_write_file(config_path):
        reasons.append(
            f"remote repository config path is not writable by current user: {config_path}{root_owned_hint(config_path.parent)}"
        )
    return reasons


def _load_hosts_or_raise(config: ResolvedManagerConfig) -> list[RemoteHostDefinition]:
    try:
        return load_remote_host_list(config)
    except FileNotFoundError as exc:
        raise KeywharfError(
            "Remote repository config not found. Run 'keywharf pull' to clone or sync it first.",
            exit_code=2,
        ) from exc


def _persist_remote_hosts(
    config: ResolvedManagerConfig,
    hosts: list[RemoteHostDefinition],
) -> None:
    validation = validate_remote_host_definitions(config, hosts)
    errors = [error for error in validation.errors if error != "Remote repository config is empty."]
    if errors:
        raise KeywharfError("\n".join(errors))
    write_remote_repo_entries(config, [host.to_dict() for host in hosts])


def _find_host_index(
    hosts: list[RemoteHostDefinition],
    server_name: str,
) -> tuple[int, RemoteHostDefinition]:
    for index, host in enumerate(hosts):
        if host.server_name == server_name:
            return index, host
    raise KeywharfError(f"Remote host '{server_name}' not found.")


def _resolve_target_endpoint(
    host: RemoteHostDefinition,
    server_name: str,
    target_name: str | None,
) -> int:
    return _resolve_named_target(
        host.endpoints,
        server_name=server_name,
        target_name=target_name,
        label="endpoint",
        option_name="--target-endpoint",
    )


def _resolve_target_auth(
    host: RemoteHostDefinition,
    server_name: str,
    target_name: str | None,
) -> int:
    return _resolve_named_target(
        host.authentication,
        server_name=server_name,
        target_name=target_name,
        label="authentication",
        option_name="--target-auth",
    )


def _resolve_named_target(
    options: list[RemoteEndpointOption] | list[RemoteAuthenticationOption],
    *,
    server_name: str,
    target_name: str | None,
    label: str,
    option_name: str,
) -> int:
    if not options:
        raise KeywharfError(f"Remote host '{server_name}' has no {label} options.")
    if target_name is None:
        if len(options) == 1:
            return 0
        raise KeywharfError(
            f"Remote host '{server_name}' has multiple {label} options. Pass {option_name}."
        )
    for index, option in enumerate(options):
        if option.name == target_name:
            return index
    raise KeywharfError(
        f"Remote host '{server_name}' has no {label} named '{target_name}'."
    )


def _selection_warnings(
    config: ResolvedManagerConfig,
    *,
    old_server_name: str | None = None,
    new_server_name: str | None = None,
    old_endpoint_name: str | None = None,
    new_endpoint_name: str | None = None,
    old_auth_name: str | None = None,
    new_auth_name: str | None = None,
    removed_server_name: str | None = None,
) -> list[str]:
    try:
        state = load_state(config)
    except Exception:
        return []

    warnings: list[str] = []
    for selection in state.selected_hosts:
        if removed_server_name is not None and selection.server_name == removed_server_name:
            warnings.append(
                f"Local state still selects '{removed_server_name}'. Run 'keywharf validate' and re-select as needed."
            )
        if (
            old_server_name is not None
            and new_server_name is not None
            and old_server_name != new_server_name
            and selection.server_name == old_server_name
        ):
            warnings.append(
                f"Local state still refers to remote host '{old_server_name}'. Run 'keywharf validate' and update the selection."
            )
        if (
            old_server_name is not None
            and selection.server_name == old_server_name
            and old_endpoint_name is not None
            and new_endpoint_name is not None
            and old_endpoint_name != new_endpoint_name
            and selection.endpoint_name == old_endpoint_name
        ):
            warnings.append(
                f"Local state still refers to endpoint '{old_endpoint_name}' for '{old_server_name}'. Run 'keywharf validate' and update the selection."
            )
        if (
            old_server_name is not None
            and selection.server_name == old_server_name
            and old_auth_name is not None
            and new_auth_name is not None
            and old_auth_name != new_auth_name
            and selection.authentication_name == old_auth_name
        ):
            warnings.append(
                f"Local state still refers to authentication '{old_auth_name}' for '{old_server_name}'. Run 'keywharf validate' and update the selection."
            )
    return list(dict.fromkeys(warnings))


def _clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    return text or None


def _clean_required(value: str, *, label: str) -> str:
    text = value.strip()
    if not text:
        raise KeywharfError(f"{label} must not be blank.")
    return text
