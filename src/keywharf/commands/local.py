"""Local desired-state and managed-output inspection commands."""

from __future__ import annotations

import json
import re

import typer
from rich.table import Table

from keywharf.commands.context import get_manager_config
from keywharf.commands.output import (
    compile_pattern,
    console,
    selection_summary,
    summarize_host,
)
from keywharf.domain.results import LocalHostStatus
from keywharf.services.local_view import get_local_status, list_local_statuses


app = typer.Typer(
    name="local",
    no_args_is_help=True,
    help="Inspect local desired state and keywharf managed output",
)


@app.command("list")
def list_local(
    ctx: typer.Context,
    pattern: str | None = typer.Option(
        None,
        "--pattern",
        "-p",
        help="Regex to search host names (re.search).",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show desired/current host blocks."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON for scripting."),
) -> None:
    try:
        regex = compile_pattern(pattern)
    except re.error as exc:
        raise typer.BadParameter(f"Invalid regex pattern: {exc}") from exc

    statuses = _filter_statuses(list_local_statuses(get_manager_config(ctx)), regex)
    if json_output:
        typer.echo(json.dumps([item.to_dict() for item in statuses], indent=2))
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("name")
    table.add_column("status")
    table.add_column("selection")
    table.add_column("desired")
    table.add_column("current")
    for item in statuses:
        table.add_row(
            item.server_name,
            item.status,
            selection_summary(item.selection),
            summarize_host(item.desired_host) if item.desired_host is not None else "-",
            summarize_host(item.current_host) if item.current_host is not None else "-",
        )
    console.print(table)

    if verbose:
        for item in statuses:
            console.rule(item.server_name)
            _render_status_detail(item)


@app.command("show")
def show_local(
    ctx: typer.Context,
    server_name: str = typer.Argument(..., help="Selected host name to inspect."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON for scripting."),
) -> None:
    status = get_local_status(get_manager_config(ctx), server_name)
    if json_output:
        payload = status.to_dict()
        payload["desired_block"] = (
            status.desired_host.to_string(0) if status.desired_host is not None else None
        )
        payload["current_block"] = (
            status.current_host.to_string(0) if status.current_host is not None else None
        )
        typer.echo(json.dumps(payload, indent=2))
        return

    console.print(f"Host: {status.server_name}")
    console.print(f"Status: {status.status}")
    _render_status_detail(status)


def _filter_statuses(
    statuses: list[LocalHostStatus],
    regex: re.Pattern[str] | None,
) -> list[LocalHostStatus]:
    if regex is None:
        return statuses
    return [item for item in statuses if regex.search(item.server_name)]


def _render_status_detail(item: LocalHostStatus) -> None:
    if item.selection is not None:
        console.print(f"Selection: {selection_summary(item.selection)}")
    if item.resolved_selection is not None:
        endpoint_name = item.resolved_selection.endpoint.name or "<single>"
        auth_name = item.resolved_selection.authentication.name or "<single>"
        console.print(f"Resolved endpoint: {endpoint_name}")
        console.print(f"Resolved authentication: {auth_name}")
    if item.reason:
        console.print(f"Reason: {item.reason}")
    if item.desired_host is not None:
        console.print("Desired managed host block:")
        console.print(item.desired_host.to_string(0))
    if item.current_host is not None:
        console.print("Current managed host block:")
        console.print(item.current_host.to_string(0))

