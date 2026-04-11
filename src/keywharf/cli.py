"""CLI entrypoint."""

from __future__ import annotations

from pathlib import Path

import typer

from keywharf.commands import register
from keywharf.commands.context import build_cli_state
from keywharf.domain.errors import KeywharfError
from keywharf.version import __version__


app = typer.Typer(
    name="keywharf",
    help="Select SSH hosts from a host repo into local desired state, then render/apply keywharf managed SSH config fragments.",
    invoke_without_command=True,
)


@app.callback()
def callback(
    ctx: typer.Context,
    config: Path | None = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to the keywharf config.json file (defaults to resolved workspace root/config.json).",
        dir_okay=False,
        exists=False,
        readable=True,
    ),
    workspace: Path | None = typer.Option(
        None,
        "--workspace",
        help="Explicit keywharf workspace root.",
        file_okay=False,
        dir_okay=True,
        exists=False,
        readable=True,
    ),
    version: bool = typer.Option(
        False,
        "--version",
        help="Show version and exit.",
        is_eager=True,
    ),
) -> None:
    if version:
        typer.echo(__version__)
        raise typer.Exit()

    ctx.obj = build_cli_state(
        config,
        workspace.expanduser().resolve() if workspace is not None else None,
    )
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit()


register(app)


def main() -> None:
    try:
        app()
    except KeywharfError as exc:
        typer.echo(str(exc), err=True)
        raise SystemExit(exc.exit_code)


if __name__ == "__main__":
    main()
