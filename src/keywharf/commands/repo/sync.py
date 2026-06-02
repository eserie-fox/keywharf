"""Host-repo sync command."""

from __future__ import annotations

import typer

from keywharf.commands._invocation import build_command_invocation
from keywharf.commands._privilege import (
    maybe_reexec_with_sudo,
    raise_for_missing_privileges,
)
from keywharf.commands.context import get_manager_config, set_host_definitions
from keywharf.services.host_definitions import load_host_definition_map
from keywharf.services.repo_sync import (
    analyze_host_repo_sync_root_requirements,
    sync_host_repo,
)


def register(app: typer.Typer) -> None:
    @app.command("sync")
    def sync_repo_command(
        ctx: typer.Context,
        sudo: bool = typer.Option(
            False,
            "--sudo",
            help="Re-exec the full command via sudo when root is required.",
        ),
    ) -> None:
        """Clone or sync the configured host repo."""

        invocation = build_command_invocation(ctx)
        if maybe_reexec_with_sudo(
            operation="repo sync",
            sudo_requested=sudo,
            invocation=invocation,
            subject="the host repo path",
        ):
            return

        config = get_manager_config(ctx)
        raise_for_missing_privileges(
            operation="repo sync",
            reasons=analyze_host_repo_sync_root_requirements(config),
            invocation=invocation,
            subject="the host repo path",
        )
        sync_host_repo(config)
        set_host_definitions(ctx, load_host_definition_map(config))
        typer.echo(f"Synced host repo into {config.host_repo_path}.")
