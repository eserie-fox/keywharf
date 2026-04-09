"""Render command."""

from __future__ import annotations

import typer

from ssh_manager.commands.context import get_manager_config
from ssh_manager.commands.output import emit_render_result
from ssh_manager.services.render import render_selected_state


def register(app: typer.Typer) -> None:
    @app.command("render")
    def render_command(
        ctx: typer.Context,
        json_output: bool = typer.Option(False, "--json", help="Output JSON for scripting."),
    ) -> None:
        """Render the desired managed SSH config without writing files."""

        emit_render_result(render_selected_state(get_manager_config(ctx)), json_output=json_output)

