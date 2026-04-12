"""Read-only convenience facades for high-frequency inspection commands."""

from __future__ import annotations

import typer

from keywharf.commands.local import list_local, show_local
from keywharf.commands.repo.host_root import list_host_command, show_host_command


list_app = typer.Typer(
    name="list",
    no_args_is_help=True,
    help=(
        "Convenience read-only commands for frequent views. "
        "Target 'repo' means host definitions in the host repo. "
        "Canonical commands remain 'keywharf repo host list' and 'keywharf local list'."
    ),
)

show_app = typer.Typer(
    name="show",
    no_args_is_help=True,
    help=(
        "Convenience read-only commands for frequent single-item views. "
        "Target 'repo' means host definitions in the host repo. "
        "Canonical commands remain 'keywharf repo host show <server>' and "
        "'keywharf local show <server>'."
    ),
)


def register() -> None:
    list_app.command(
        "repo",
        help=(
            "Convenience command for host definitions in the host repo. "
            "Canonical: keywharf repo host list."
        ),
    )(list_host_command)
    list_app.command(
        "local",
        help=(
            "Convenience command for local desired/current status. "
            "Canonical: keywharf local list."
        ),
    )(list_local)
    show_app.command(
        "repo",
        help=(
            "Convenience command for one host definition in the host repo. "
            "Canonical: keywharf repo host show <server>."
        ),
    )(show_host_command)
    show_app.command(
        "local",
        help=(
            "Convenience command for one local desired/current status view. "
            "Canonical: keywharf local show <server>."
        ),
    )(show_local)


register()
