"""Init command."""

from __future__ import annotations

import typer

from keywharf.commands._invocation import build_command_invocation
from keywharf.commands._privilege import maybe_reexec_with_sudo, raise_for_missing_privileges
from keywharf.commands.context import get_cli_state
from keywharf.services.init import analyze_init_root_requirements, initialize_workspace


def register(app: typer.Typer) -> None:
    @app.command("init")
    def init_command(
        ctx: typer.Context,
        ssh_key_remote_repo: str = typer.Option(
            "git@example.com:org/keys.git",
            "--ssh-key-remote-repo",
            help="Remote repo URL placeholder written into the generated manager config.",
        ),
        ssh_dir: str = typer.Option(
            "~/.ssh",
            "--ssh-dir",
            help="SSH directory written into the generated manager config.",
        ),
        sudo: bool = typer.Option(
            False,
            "--sudo",
            help="Re-exec the full command via sudo when root is required.",
        ),
    ) -> None:
        """Create a minimal keywharf workspace."""

        cli_state = get_cli_state(ctx)
        resolved_data_root = cli_state.data_root_override
        invocation = build_command_invocation(ctx)
        if maybe_reexec_with_sudo(
            operation="init",
            sudo_requested=sudo,
            invocation=invocation,
            subject="the target workspace",
        ):
            return
        raise_for_missing_privileges(
            operation="init",
            reasons=analyze_init_root_requirements(
                cli_state.config_override,
                data_root=resolved_data_root,
                ssh_key_remote_repo=ssh_key_remote_repo,
                ssh_dir=ssh_dir,
            ),
            invocation=invocation,
            subject="the target workspace",
        )

        result = initialize_workspace(
            cli_state.config_override,
            data_root=resolved_data_root,
            ssh_key_remote_repo=ssh_key_remote_repo,
            ssh_dir=ssh_dir,
        )
        typer.echo(f"Initialized data root at {result.data_root}.")
        typer.echo(f"Config: {result.config_path}")
        typer.echo(f"State: {result.state_path}")
