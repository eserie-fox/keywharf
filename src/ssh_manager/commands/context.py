"""CLI context assembly and lazy service loading."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import cast

import typer

from ssh_manager.domain.errors import SSHManagerError
from ssh_manager.domain.models import ManagerConfig, RemoteHostDefinition, SSHHostConfig
from ssh_manager.runtime.config import load_manager_config
from ssh_manager.services.local_hosts import load_local_hosts
from ssh_manager.services.pull import pull_remote_repo
from ssh_manager.services.remote_hosts import load_remote_host_map, remote_host_map_to_dict


@dataclass
class CLIState:
    config_override: Path | None
    auto_pull: bool
    manager_config: ManagerConfig | None = None
    current_hosts: list[SSHHostConfig] | None = None
    remote_hosts: dict[str, RemoteHostDefinition] | None = None
    auto_pull_attempted: bool = False


def build_cli_state(config_override: Path | None, auto_pull: bool) -> CLIState:
    return CLIState(config_override=config_override, auto_pull=auto_pull)


def _require_state(ctx: typer.Context) -> CLIState:
    state = cast(CLIState | None, ctx.obj)
    if state is None:
        raise SSHManagerError("CLI context was not initialized; this is unexpected.")
    return state


def get_manager_config(ctx: typer.Context) -> ManagerConfig:
    state = _require_state(ctx)
    if state.manager_config is not None:
        return state.manager_config

    try:
        state.manager_config = load_manager_config(state.config_override)
    except FileNotFoundError as exc:
        missing_path = exc.filename or str(exc)
        raise SSHManagerError(
            f"Config file not found at {missing_path}. Provide --config or create it first.",
            exit_code=2,
        ) from exc
    except RuntimeError as exc:
        raise SSHManagerError(str(exc), exit_code=2) from exc

    if state.auto_pull and not state.auto_pull_attempted:
        pull_remote_repo(state.manager_config)
        state.auto_pull_attempted = True

    return state.manager_config


def get_current_hosts(ctx: typer.Context) -> list[SSHHostConfig]:
    state = _require_state(ctx)
    if state.current_hosts is None:
        state.current_hosts = load_local_hosts(get_manager_config(ctx))
    return state.current_hosts


def set_current_hosts(ctx: typer.Context, hosts: list[SSHHostConfig]) -> None:
    _require_state(ctx).current_hosts = hosts


def get_remote_hosts(ctx: typer.Context) -> dict[str, RemoteHostDefinition]:
    state = _require_state(ctx)
    if state.remote_hosts is not None:
        return state.remote_hosts

    config = get_manager_config(ctx)
    try:
        state.remote_hosts = load_remote_host_map(config)
    except FileNotFoundError as exc:
        if state.auto_pull and not state.auto_pull_attempted:
            pull_remote_repo(config)
            state.auto_pull_attempted = True
            state.remote_hosts = load_remote_host_map(config)
        else:
            raise SSHManagerError(
                "Remote repository config not found. Run 'ssh-manager pull' to clone/sync it first.",
                exit_code=2,
            ) from exc
    return state.remote_hosts


def set_remote_hosts(
    ctx: typer.Context, remote_hosts: dict[str, RemoteHostDefinition]
) -> None:
    _require_state(ctx).remote_hosts = remote_hosts


def clear_remote_hosts(ctx: typer.Context) -> None:
    _require_state(ctx).remote_hosts = None


def get_remote_hosts_as_dict(ctx: typer.Context) -> dict[str, dict[str, object]]:
    return remote_host_map_to_dict(get_remote_hosts(ctx))
