"""Pull command."""

from __future__ import annotations

import typer

from keywharf.commands._invocation import build_command_invocation
from keywharf.commands._privilege import maybe_reexec_with_sudo, raise_for_missing_privileges
from keywharf.commands.context import get_manager_config, set_remote_hosts
from keywharf.services.pull import analyze_pull_root_requirements, pull_remote_repo
from keywharf.services.remote_hosts import load_remote_host_map


def register(app: typer.Typer) -> None:
    @app.command("pull")
    def pull_command(
        ctx: typer.Context,
        sudo: bool = typer.Option(
            False,
            "--sudo",
            help="Re-exec the full command via sudo when root is required.",
        ),
    ) -> None:
        """Clone or update the configured remote repo."""

        invocation = build_command_invocation(ctx)
        if maybe_reexec_with_sudo(
            operation="pull",
            sudo_requested=sudo,
            invocation=invocation,
            subject="the local repo path",
        ):
            return

        config = get_manager_config(ctx)
        raise_for_missing_privileges(
            operation="pull",
            reasons=analyze_pull_root_requirements(config),
            invocation=invocation,
            subject="the local repo path",
        )
        pull_remote_repo(config)
        set_remote_hosts(ctx, load_remote_host_map(config))
        typer.echo(f"Synced remote repo into {config.ssh_key_local_repo}.")

