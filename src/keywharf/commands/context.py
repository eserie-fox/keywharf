"""CLI context assembly and lazy runtime loading."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import cast

import typer
from pydantic import ValidationError

from keywharf.config.loader import load_resolved_manager_config
from keywharf.config.resolver import ResolvedManagerConfig
from keywharf.domain.errors import KeywharfError
from keywharf.domain.models import HostDefinition
from keywharf.services.host_definitions import load_host_definition_map
from keywharf.services.host_repo_setup import missing_host_repo_config_message


@dataclass(slots=True)
class CLIState:
    config_override: Path | None
    workspace_override: Path | None
    manager_config: ResolvedManagerConfig | None = None
    host_definitions: dict[str, HostDefinition] | None = None


def build_cli_state(config_override: Path | None, workspace_override: Path | None) -> CLIState:
    return CLIState(
        config_override=config_override,
        workspace_override=workspace_override,
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
            workspace_root=state.workspace_override,
        )
    except FileNotFoundError as exc:
        missing_path = exc.filename or str(exc)
        raise KeywharfError(
            f"Config file not found at {missing_path}. The workspace marker was found, "
            "but config.json is missing. Provide --config or create a new workspace with "
            "'keywharf init <workspace_name>'.",
            exit_code=2,
        ) from exc
    except ValidationError as exc:
        raise KeywharfError(f"Invalid manager config: {exc}", exit_code=2) from exc
    except RuntimeError as exc:
        raise KeywharfError(str(exc), exit_code=2) from exc
    except OSError as exc:
        raise KeywharfError(f"Failed to load manager config: {exc}", exit_code=2) from exc

    return state.manager_config


def get_host_definitions(ctx: typer.Context) -> dict[str, HostDefinition]:
    state = _require_state(ctx)
    if state.host_definitions is not None:
        return state.host_definitions

    config = get_manager_config(ctx)
    try:
        state.host_definitions = load_host_definition_map(config)
    except FileNotFoundError as exc:
        raise KeywharfError(missing_host_repo_config_message(config), exit_code=2) from exc
    return state.host_definitions


def set_host_definitions(ctx: typer.Context, host_definitions: dict[str, HostDefinition]) -> None:
    _require_state(ctx).host_definitions = host_definitions
