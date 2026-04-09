"""Typer command registration."""

from __future__ import annotations

import typer

from keywharf.commands import apply, deselect, init, install_include, local, pull, render, select, validate
from keywharf.commands.remote.group import app as remote_app


def register(app: typer.Typer) -> None:
    for module in [init, pull, validate, render, apply, install_include, select, deselect]:
        module.register(app)
    app.add_typer(local.app, name="local")
    app.add_typer(remote_app, name="remote")
