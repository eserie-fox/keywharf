"""Host repo command groups."""

from __future__ import annotations

import typer

from keywharf.commands.repo.host_auth import register as register_auth_commands
from keywharf.commands.repo.host_endpoint import register as register_endpoint_commands
from keywharf.commands.repo.host_root import register as register_host_root_commands


def register(app: typer.Typer) -> None:
    endpoint_app = typer.Typer(
        name="endpoint",
        no_args_is_help=True,
        help="Manage named endpoint options for one host.",
    )
    auth_app = typer.Typer(
        name="auth",
        no_args_is_help=True,
        help="Manage named authentication options for one host.",
    )

    register_host_root_commands(app)
    register_endpoint_commands(endpoint_app)
    register_auth_commands(auth_app)

    app.add_typer(endpoint_app, name="endpoint")
    app.add_typer(auth_app, name="auth")
