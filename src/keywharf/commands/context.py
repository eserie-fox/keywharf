"""CLI context assembly and lazy runtime loading."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import cast

from pydantic import ValidationError
import typer

from keywharf.config.loader import load_resolved_manager_config
from keywharf.config.resolver import ResolvedManagerConfig
from keywharf.domain.errors import KeywharfError
from keywharf.domain.models import RemoteHostDefinition
from keywharf.services.remote_hosts import load_remote_host_map


@dataclass(slots=True)
class CLIState:
    config_override: Path | None
    data_root_override: Path | None
    manager_config: ResolvedManagerConfig | None = None
    remote_hosts: dict[str, RemoteHostDefinition] | None = None


def build_cli_state(config_override: Path | None, data_root_override: Path | None) -> CLIState:
    return CLIState(
        config_override=config_override,
        data_root_override=data_root_override,
    )


def _require_state(ctx: typer.Context) -> CLIState:
    state = cast(CLIState | None, ctx.obj)
    if state is None:
        raise KeywharfError("CLI context was not initialized; this is unexpected.")
    return state


def get_cli_state(ctx: typer.Context) -> CLIState:
    return _require_state(ctx)


def get_manager_config(ctx: typer.Context) -> ResolvedManagerConfig:
    state = _require_state(ctx)
    if state.manager_config is not None:
        return state.manager_config

    try:
        state.manager_config = load_resolved_manager_config(
            state.config_override,
            data_root=state.data_root_override,
        )
    except FileNotFoundError as exc:
        missing_path = exc.filename or str(exc)
        raise KeywharfError(
            f"Config file not found at {missing_path}. Provide --config or run 'keywharf init' first.",
            exit_code=2,
        ) from exc
    except ValidationError as exc:
        raise KeywharfError(f"Invalid manager config: {exc}", exit_code=2) from exc
    except RuntimeError as exc:
        raise KeywharfError(str(exc), exit_code=2) from exc
    except OSError as exc:
        raise KeywharfError(f"Failed to load manager config: {exc}", exit_code=2) from exc

    return state.manager_config


def get_remote_hosts(ctx: typer.Context) -> dict[str, RemoteHostDefinition]:
    state = _require_state(ctx)
    if state.remote_hosts is not None:
        return state.remote_hosts

    try:
        state.remote_hosts = load_remote_host_map(get_manager_config(ctx))
    except FileNotFoundError as exc:
        raise KeywharfError(
            "Remote repository config not found. Run 'keywharf pull' to clone/sync it first.",
            exit_code=2,
        ) from exc
    return state.remote_hosts


def set_remote_hosts(ctx: typer.Context, remote_hosts: dict[str, RemoteHostDefinition]) -> None:
    _require_state(ctx).remote_hosts = remote_hosts
