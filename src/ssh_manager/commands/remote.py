"""Remote host inspection commands."""

from __future__ import annotations

import json
import re

import typer
from rich.console import Console
from rich.table import Table

from ssh_manager.commands.context import get_remote_hosts
from ssh_manager.commands.output import (
    compile_pattern,
    filter_names,
    render_auth_table,
    render_endpoint_table,
)
from ssh_manager.domain.errors import SSHManagerError


console = Console()
app = typer.Typer(
    name="remote",
    no_args_is_help=True,
    help="Inspect remote repo configs and stable selectors",
)


@app.command("list")
def list_remote(
    ctx: typer.Context,
    pattern: str | None = typer.Option(
        None,
        "--pattern",
        "-p",
        help="Regex to search remote config names (re.search).",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show full remote config entries."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON for scripting."),
) -> None:
    try:
        regex = compile_pattern(pattern)
    except re.error as exc:
        raise typer.BadParameter(f"Invalid regex pattern: {exc}") from exc

    remote_hosts = get_remote_hosts(ctx)
    names = filter_names(sorted(remote_hosts.keys()), regex)

    if json_output:
        payload = (
            {name: remote_hosts[name].to_dict() for name in names}
            if verbose
            else names
        )
        typer.echo(json.dumps(payload, indent=2))
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("index", justify="right", style="cyan")
    table.add_column("config_name")
    for index, name in enumerate(names):
        table.add_row(str(index), name)
    console.print(table)

    if verbose:
        for name in names:
            console.rule(name)
            console.print(json.dumps(remote_hosts[name].to_dict(), indent=2))


@app.command("show")
def show_remote(
    ctx: typer.Context,
    config_name: str = typer.Argument(..., help="Remote config name to inspect."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON for scripting."),
) -> None:
    remote_hosts = get_remote_hosts(ctx)
    remote_host = remote_hosts.get(config_name)
    if remote_host is None:
        raise SSHManagerError(
            f"Remote config '{config_name}' not found. Run 'ssh-manager remote list' to see available names."
        )

    if json_output:
        typer.echo(json.dumps(remote_host.to_dict(), indent=2))
        return

    console.print(f"Remote config: {config_name}")
    console.print(render_endpoint_table(remote_host.endpoints))
    console.print(render_auth_table(remote_host.authentication))

    if remote_host.extra_config:
        table = Table(show_header=True, header_style="bold")
        table.add_column("index", justify="right", style="cyan")
        table.add_column("Key")
        table.add_column("Value")
        table.add_column("Comment")
        for index, item in enumerate(remote_host.extra_config):
            table.add_row(
                str(index),
                item.key or "",
                item.value or "",
                item.comment or "",
            )
        console.print(table)
