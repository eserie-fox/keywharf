"""Install-include command."""

from __future__ import annotations

import typer

from ssh_manager.commands._invocation import build_command_invocation
from ssh_manager.commands._privilege import maybe_reexec_with_sudo, raise_for_missing_privileges
from ssh_manager.commands.context import get_manager_config
from ssh_manager.commands.output import console
from ssh_manager.services.install_include import (
    analyze_install_include_root_requirements,
    install_managed_include,
)


def register(app: typer.Typer) -> None:
    @app.command("install-include")
    def install_include_command(
        ctx: typer.Context,
        dry_run: bool = typer.Option(False, "--dry-run", help="Preview without writing files."),
        sudo: bool = typer.Option(
            False,
            "--sudo",
            help="Re-exec the full command via sudo when root is required.",
        ),
    ) -> None:
        """Install or preview the managed-config Include in the main SSH config."""

        invocation = build_command_invocation(ctx)
        if not dry_run and maybe_reexec_with_sudo(
            operation="install-include",
            sudo_requested=sudo,
            invocation=invocation,
            subject="the main SSH config",
        ):
            return

        config = get_manager_config(ctx)
        if not dry_run:
            raise_for_missing_privileges(
                operation="install-include",
                reasons=analyze_install_include_root_requirements(config),
                invocation=invocation,
                subject="the main SSH config",
            )

        result = install_managed_include(config, dry_run=dry_run)
        if result.already_present:
            typer.echo(f"Include already present in {result.main_config_path}.")
            return
        if dry_run:
            console.print(
                f"Dry run: would update {result.main_config_path} with `{result.include_line}`."
            )
            console.print(result.rendered_content)
            return
        typer.echo(
            f"Installed Include into {result.main_config_path} for {result.managed_config_path}."
        )

