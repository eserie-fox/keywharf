"""Typer command registration."""

from __future__ import annotations

import typer

from keywharf.commands import (
    apply,
    convenience,
    deselect,
    init,
    install_include,
    local,
    render,
    select,
    validate,
)
from keywharf.commands.repo.group import app as repo_app


def register(app: typer.Typer) -> None:
    for module in [init, validate, render, apply, install_include, select, deselect]:
        module.register(app)
    app.add_typer(local.app, name="local")
    app.add_typer(repo_app, name="repo")
    app.add_typer(convenience.list_app, name="list")
    app.add_typer(convenience.show_app, name="show")
