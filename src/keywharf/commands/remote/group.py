"""Remote command groups."""

from __future__ import annotations

import typer

from keywharf.commands.remote.host import register as register_host_commands


app = typer.Typer(
    name="remote",
    no_args_is_help=True,
    help="Inspect and edit the local checkout of the remote host repository.",
)
host_app = typer.Typer(
    name="host",
    no_args_is_help=True,
    help="List, show, and edit remote host definitions in the local repo checkout.",
)

register_host_commands(host_app)
app.add_typer(host_app, name="host")
