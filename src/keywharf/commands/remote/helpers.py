"""Remote command helpers."""

from __future__ import annotations

from collections.abc import Callable

import typer

from keywharf.commands._invocation import build_command_invocation
from keywharf.commands._privilege import maybe_reexec_with_sudo, raise_for_missing_privileges
from keywharf.commands.context import get_manager_config
from keywharf.config.resolver import ResolvedManagerConfig
from keywharf.domain.results import RemoteHostMutationResult
from keywharf.services.remote_host_editor import analyze_remote_host_write_root_requirements


RemoteHostMutationAction = Callable[[ResolvedManagerConfig], RemoteHostMutationResult]


def run_remote_host_mutation(
    ctx: typer.Context,
    *,
    command_name: str,
    sudo: bool,
    action: RemoteHostMutationAction,
) -> RemoteHostMutationResult | None:
    invocation = build_command_invocation(ctx)
    if maybe_reexec_with_sudo(
        operation=command_name,
        sudo_requested=sudo,
        invocation=invocation,
        subject="the local remote repo config",
    ):
        return None

    config = get_manager_config(ctx)
    raise_for_missing_privileges(
        operation=command_name,
        reasons=analyze_remote_host_write_root_requirements(config),
        invocation=invocation,
        subject="the local remote repo config",
    )
    return action(config)
