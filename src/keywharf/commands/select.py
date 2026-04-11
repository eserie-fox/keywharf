"""Select command."""

from __future__ import annotations

import typer

from keywharf.commands._invocation import build_command_invocation
from keywharf.commands._privilege import maybe_reexec_with_sudo, raise_for_missing_privileges
from keywharf.commands._selection_prompt import complete_selection_names
from keywharf.commands.context import get_host_definitions, get_manager_config
from keywharf.services.selections import analyze_select_root_requirements, select_host


def register(app: typer.Typer) -> None:
    @app.command("select")
    def select_command(
        ctx: typer.Context,
        server_name: str = typer.Argument(..., help="Host name to select from the host repo."),
        endpoint: str | None = typer.Option(
            None,
            "--endpoint",
            help="Stable EndPointName to select. Omit to auto-select a singleton endpoint or prompt in an interactive terminal.",
        ),
        auth: str | None = typer.Option(
            None,
            "--auth",
            help="Stable AuthenticationName to select. Omit to auto-select a singleton authentication or prompt in an interactive terminal.",
        ),
        sudo: bool = typer.Option(
            False,
            "--sudo",
            help="Re-exec the full command via sudo when root is required.",
        ),
    ) -> None:
        """Upsert one desired host selection into local state."""

        invocation = build_command_invocation(ctx)
        if maybe_reexec_with_sudo(
            operation="select",
            sudo_requested=sudo,
            invocation=invocation,
            subject="the state file",
        ):
            return

        config = get_manager_config(ctx)
        raise_for_missing_privileges(
            operation="select",
            reasons=analyze_select_root_requirements(config),
            invocation=invocation,
            subject="the state file",
        )
        host_definitions = get_host_definitions(ctx)
        endpoint_name, authentication_name = complete_selection_names(
            host_definitions,
            server_name=server_name,
            endpoint_name=endpoint,
            authentication_name=auth,
        )
        _, selection = select_host(
            config,
            host_definitions,
            server_name=server_name,
            endpoint_name=endpoint_name,
            authentication_name=authentication_name,
        )
        typer.echo(
            f"Selected '{selection.server_name}' in local state. "
            "Run 'keywharf apply' to materialize the managed config."
        )
