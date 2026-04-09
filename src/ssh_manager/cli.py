"""CLI entrypoint."""

from __future__ import annotations

from pathlib import Path

import typer

from ssh_manager.commands import register
from ssh_manager.commands.context import build_cli_state
from ssh_manager.domain.errors import SSHManagerError
from ssh_manager.version import __version__


app = typer.Typer(
    name="ssh-manager",
    help="Manage local SSH config alongside a remote key repository.",
    invoke_without_command=True,
)


@app.callback()
def callback(
    ctx: typer.Context,
    config: Path | None = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to the ssh-manager config.json file (defaults to resolved data root/config.json).",
        dir_okay=False,
        exists=False,
        readable=True,
    ),
    auto_pull: bool = typer.Option(
        False,
        "--auto-pull",
        help="Automatically pull the remote repo before command execution.",
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

    ctx.obj = build_cli_state(config, auto_pull)
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit()


register(app)


def main() -> None:
    try:
        app()
    except SSHManagerError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=exc.exit_code) from exc


if __name__ == "__main__":
    main()
