"""Typer command registration."""

from __future__ import annotations

import typer

from ssh_manager.commands import local, manage, remote


def register(app: typer.Typer) -> None:
    app.add_typer(local.app, name="local")
    app.add_typer(remote.app, name="remote")
    manage.register(app)
