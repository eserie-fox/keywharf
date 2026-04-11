"""Repo command groups."""

from __future__ import annotations

import typer

from keywharf.commands.repo.host import register as register_host_commands
from keywharf.commands.repo.init import register as register_repo_init_command
from keywharf.commands.repo.sync import register as register_repo_sync_command


app = typer.Typer(
    name="repo",
    no_args_is_help=True,
    help="Bootstrap, sync, and inspect the workspace host repo.",
)
host_app = typer.Typer(
    name="host",
    no_args_is_help=True,
    help="List, show, and edit host definitions in the host repo.",
)

register_repo_init_command(app)
register_repo_sync_command(app)
register_host_commands(host_app)
app.add_typer(host_app, name="host")
