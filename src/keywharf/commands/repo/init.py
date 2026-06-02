"""Host-repo bootstrap command."""

from __future__ import annotations

import typer

from keywharf.commands._invocation import build_command_invocation
from keywharf.commands._privilege import (
    maybe_reexec_with_sudo,
    raise_for_missing_privileges,
)
from keywharf.commands.context import get_manager_config
from keywharf.services.repo_init import (
    analyze_host_repo_init_root_requirements,
    initialize_host_repo,
)


def register(app: typer.Typer) -> None:
    @app.command("init")
    def init_repo_command(
        ctx: typer.Context,
        sudo: bool = typer.Option(
            False,
            "--sudo",
            help="Re-exec the full command via sudo when root is required.",
        ),
    ) -> None:
        """Bootstrap a local host repo skeleton without git initialization."""

        invocation = build_command_invocation(ctx)
        if maybe_reexec_with_sudo(
            operation="repo init",
            sudo_requested=sudo,
            invocation=invocation,
            subject="the host repo path",
        ):
            return

        config = get_manager_config(ctx)
        raise_for_missing_privileges(
            operation="repo init",
            reasons=analyze_host_repo_init_root_requirements(config),
            invocation=invocation,
            subject="the host repo path",
        )
        result = initialize_host_repo(config)
        typer.echo(f"Initialized host repo: {result.host_repo_path}")
        typer.echo("Created paths:")
        for path in result.created_paths:
            typer.echo(f"- {path}")
