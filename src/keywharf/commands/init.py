"""Init command."""

from __future__ import annotations

from pathlib import Path

import typer

from keywharf.commands._invocation import build_command_invocation
from keywharf.commands._privilege import maybe_reexec_with_sudo, raise_for_missing_privileges
from keywharf.commands.context import get_cli_state
from keywharf.domain.errors import KeywharfError
from keywharf.services.init import analyze_init_root_requirements, initialize_workspace


def register(app: typer.Typer) -> None:
    @app.command("init")
    def init_command(
        ctx: typer.Context,
        workspace_name: str = typer.Argument(..., help="Name of the new workspace directory."),
        directory: Path = typer.Option(
            Path("."),
            "--directory",
            help="Base directory under which the new workspace directory will be created.",
            file_okay=False,
            dir_okay=True,
            exists=False,
            readable=True,
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
        """Create a new named workspace directory."""

        cli_state = get_cli_state(ctx)
        if cli_state.config_override is not None:
            raise KeywharfError("`keywharf init` does not accept --config.", exit_code=2)
        if cli_state.workspace_override is not None:
            raise KeywharfError(
                "`keywharf init` does not accept --workspace. Use `init <workspace_name> --directory <base_dir>`.",
                exit_code=2,
            )

        base_dir = directory.expanduser().resolve()
        invocation = build_command_invocation(ctx, overrides={"directory": base_dir})
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
                workspace_name,
                base_dir=base_dir,
            ),
            invocation=invocation,
            subject="the target workspace",
        )

        result = initialize_workspace(
            workspace_name,
            base_dir=base_dir,
            ssh_dir=ssh_dir,
        )
        typer.echo(f"Created workspace: {result.workspace_root}")
        typer.echo("Created paths:")
        for path in result.created_paths:
            typer.echo(f"- {path}")
        typer.echo("")
        typer.echo(f"Default host repo path: {result.host_repo_path}")
        typer.echo(
            "`keywharf init` created that directory as an empty workspace repo. "
            "Run `repo init` to write `config.json`, `keys/`, and `.gitignore`."
        )
        typer.echo("")
        typer.echo("Next steps:")
        typer.echo("A. You already have a host repo remote URL:")
        typer.echo(f"- Edit {result.config_path} and set host_repo_remote_url.")
        typer.echo(f"- Run: keywharf --workspace {result.workspace_root} repo sync")
        typer.echo("B. You are starting from scratch:")
        typer.echo(f"- Run: keywharf --workspace {result.workspace_root} repo init")
        typer.echo(f"- Then: keywharf --workspace {result.workspace_root} repo host add <server> --hostname <host> --user <user> --identity-file keys/<id_file>")
        typer.echo(f"- If you want a real git repo later, run git init / git remote add / commit / push yourself in {result.host_repo_path}.")
