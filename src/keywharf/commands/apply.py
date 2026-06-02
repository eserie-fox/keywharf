"""Apply command."""

from __future__ import annotations

import json

import typer

from keywharf.commands._invocation import build_command_invocation
from keywharf.commands._privilege import (
    maybe_reexec_with_sudo,
    raise_for_missing_privileges,
)
from keywharf.commands.context import get_manager_config
from keywharf.commands.output import emit_render_result
from keywharf.services.apply import (
    analyze_apply_root_requirements,
    apply_selected_state,
)
from keywharf.services.render import render_selected_state


def register(app: typer.Typer) -> None:
    @app.command("apply")
    def apply_command(
        ctx: typer.Context,
        backup: bool = typer.Option(
            True,
            "--backup/--no-backup",
            help="Create a timestamped backup before replacing the managed config fragment.",
        ),
        dry_run: bool = typer.Option(False, "--dry-run", help="Preview without writing files."),
        allow_empty: bool = typer.Option(
            False,
            "--allow-empty",
            help="Allow apply to clear a non-empty managed config when local state is empty.",
        ),
        json_output: bool = typer.Option(False, "--json", help="Output JSON for scripting."),
        sudo: bool = typer.Option(
            False,
            "--sudo",
            help="Re-exec the full command via sudo when root is required.",
        ),
    ) -> None:
        """Validate, materialize keys, and atomically replace the managed config."""

        invocation = build_command_invocation(ctx)
        if not dry_run and maybe_reexec_with_sudo(
            operation="apply",
            sudo_requested=sudo,
            invocation=invocation,
            subject="manager-owned files",
        ):
            return

        config = get_manager_config(ctx)
        preview = render_selected_state(config)
        if not dry_run:
            raise_for_missing_privileges(
                operation="apply",
                reasons=analyze_apply_root_requirements(config, preview, backup=backup),
                invocation=invocation,
                subject="manager-owned files",
            )

        result = apply_selected_state(
            config,
            backup=backup,
            dry_run=dry_run,
            allow_empty=allow_empty,
        )
        if json_output:
            typer.echo(json.dumps(result.to_dict(), indent=2))
            return
        if dry_run:
            emit_render_result(result.render_result, json_output=False)
            typer.echo("Dry run: no files were written.", err=True)
            return

        for warning in result.warnings:
            typer.echo(f"WARNING: {warning}", err=True)
        typer.echo(f"Applied managed config at {result.managed_config_path}.")
        if result.copied_keys:
            typer.echo(f"Copied keys: {len(result.copied_keys)}")
        if result.deleted_keys:
            typer.echo(f"Deleted stale keys: {len(result.deleted_keys)}")
