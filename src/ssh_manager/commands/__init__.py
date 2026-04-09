"""Typer command registration."""

from __future__ import annotations

import typer

from ssh_manager.commands import (
    apply,
    deselect,
    init,
    install_include,
    local,
    pull,
    remote,
    render,
    select,
    validate,
)


def register(app: typer.Typer) -> None:
    for module in [init, pull, validate, render, apply, install_include, select, deselect]:
        module.register(app)
    app.add_typer(local.app, name="local")
    app.add_typer(remote.app, name="remote")

