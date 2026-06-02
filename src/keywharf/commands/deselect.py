"""Deselect command."""

from __future__ import annotations

import typer

from keywharf.commands._invocation import build_command_invocation
from keywharf.commands._privilege import (
    maybe_reexec_with_sudo,
    raise_for_missing_privileges,
)
from keywharf.commands.context import get_manager_config
from keywharf.services.selections import (
    analyze_deselect_root_requirements,
    deselect_host,
)


def register(app: typer.Typer) -> None:
    @app.command("deselect")
    def deselect_command(
        ctx: typer.Context,
        server_name: str = typer.Argument(
            ..., help="Selected host name to remove from local state."
        ),
        sudo: bool = typer.Option(
            False,
            "--sudo",
            help="Re-exec the full command via sudo when root is required.",
        ),
    ) -> None:
        """Remove one desired host selection from local state."""

        invocation = build_command_invocation(ctx)
        if maybe_reexec_with_sudo(
            operation="deselect",
            sudo_requested=sudo,
            invocation=invocation,
            subject="the state file",
        ):
            return

        config = get_manager_config(ctx)
        raise_for_missing_privileges(
            operation="deselect",
            reasons=analyze_deselect_root_requirements(config),
            invocation=invocation,
            subject="the state file",
        )
        _, selection = deselect_host(config, server_name=server_name)
        typer.echo(
            f"Deselected '{selection.server_name}' from local state. "
            "Run 'keywharf apply' to materialize the managed config."
        )
