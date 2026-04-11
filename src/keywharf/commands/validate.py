"""Validate command."""

from __future__ import annotations

import typer

from keywharf.commands.context import get_manager_config
from keywharf.commands.output import emit_validation_result
from keywharf.services.validate import validate_workspace


def register(app: typer.Typer) -> None:
    @app.command("validate")
    def validate_command(
        ctx: typer.Context,
        json_output: bool = typer.Option(False, "--json", help="Output JSON for scripting."),
    ) -> None:
        """Validate config, host repo content, and local state."""

        emit_validation_result(validate_workspace(get_manager_config(ctx)), json_output=json_output)
