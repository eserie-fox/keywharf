"""Local SSH config inspection commands."""

from __future__ import annotations

import json
import re

import typer
from rich.console import Console
from rich.table import Table

from ssh_manager.commands.context import get_current_hosts
from ssh_manager.commands.output import compile_pattern, filter_hosts, summarize_host


console = Console()
app = typer.Typer(name="local", no_args_is_help=True, help="Inspect local ssh config")


@app.command("list")
def list_local(
    ctx: typer.Context,
    pattern: str | None = typer.Option(
        None,
        "--pattern",
        "-p",
        help="Regex to search host names (re.search).",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show full host blocks."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON for scripting."),
) -> None:
    try:
        regex = compile_pattern(pattern)
    except re.error as exc:
        raise typer.BadParameter(f"Invalid regex pattern: {exc}") from exc

    hosts = filter_hosts(get_current_hosts(ctx), regex)
    if json_output:
        typer.echo(json.dumps([host.to_dict() for host in hosts], indent=2))
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("index", justify="right", style="cyan")
    table.add_column("name")
    table.add_column("summary")
    for index, host in enumerate(hosts):
        table.add_row(str(index), host.name or "", summarize_host(host))
    console.print(table)

    if verbose:
        for host in hosts:
            console.rule(host.name or "")
            console.print(host.to_string(0))
