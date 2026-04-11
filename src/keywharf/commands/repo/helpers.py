"""Repo command helpers."""

from __future__ import annotations

from collections.abc import Callable

import typer

from keywharf.commands._invocation import build_command_invocation
from keywharf.commands._privilege import maybe_reexec_with_sudo, raise_for_missing_privileges
from keywharf.commands.context import get_manager_config
from keywharf.config.resolver import ResolvedManagerConfig
from keywharf.domain.results import HostDefinitionMutationResult
from keywharf.services.host_definition_editor import analyze_host_definition_write_root_requirements


HostDefinitionMutationAction = Callable[[ResolvedManagerConfig], HostDefinitionMutationResult]


def run_host_definition_mutation(
    ctx: typer.Context,
    *,
    command_name: str,
    sudo: bool,
    action: HostDefinitionMutationAction,
) -> HostDefinitionMutationResult | None:
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
        reasons=analyze_host_definition_write_root_requirements(config),
        invocation=invocation,
        subject="the host repo config",
    )
    return action(config)
