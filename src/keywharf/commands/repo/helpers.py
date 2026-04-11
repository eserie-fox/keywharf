"""Repo command helpers."""

from __future__ import annotations

from collections.abc import Callable

import typer

from keywharf.commands._invocation import build_command_invocation
from keywharf.commands._privilege import maybe_reexec_with_sudo, raise_for_missing_privileges
from keywharf.commands.context import get_manager_config
from keywharf.config.resolver import ResolvedManagerConfig
from keywharf.domain.results import HostRepoMutationResult
from keywharf.services.host_repo_editor_common import (
    analyze_host_repo_config_write_root_requirements,
)


HostRepoMutationAction = Callable[[ResolvedManagerConfig], HostRepoMutationResult]


def run_host_repo_mutation(
    ctx: typer.Context,
    *,
    command_name: str,
    sudo: bool,
    action: HostRepoMutationAction,
) -> HostRepoMutationResult | None:
    invocation = build_command_invocation(ctx)
    if maybe_reexec_with_sudo(
        operation=command_name,
        sudo_requested=sudo,
        invocation=invocation,
        subject="the host repo config",
    ):
        return None

    config = get_manager_config(ctx)
    raise_for_missing_privileges(
        operation=command_name,
        reasons=analyze_host_repo_config_write_root_requirements(config),
        invocation=invocation,
        subject="the host repo config",
    )
    return action(config)


def reject_option_and_clear_flag(
    *,
    value: object | None,
    clear: bool,
    option_name: str,
    clear_name: str,
) -> None:
    if value is None or not clear:
        return
    raise typer.BadParameter(f"{option_name} cannot be used with {clear_name}.")
