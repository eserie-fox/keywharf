"""CLI-oriented formatting helpers."""

from __future__ import annotations

import json
import re

import typer
from rich.console import Console
from rich.table import Table

from ssh_manager.domain.models import (
    RemoteAuthenticationOption,
    RemoteEndpointOption,
    SelectedHostState,
    SSHHostConfig,
)
from ssh_manager.domain.results import RenderResult, ValidationResult


console = Console()


def compile_pattern(pattern: str | None) -> re.Pattern[str] | None:
    if not pattern:
        return None
    return re.compile(pattern)


def filter_names(items: list[str], pattern: re.Pattern[str] | None) -> list[str]:
    if pattern is None:
        return items
    return [item for item in items if pattern.search(item)]


def summarize_host(host: SSHHostConfig) -> str:
    parts: list[str] = []
    if host.endpoint.hostname:
        if host.endpoint.port is not None:
            parts.append(f"{host.endpoint.hostname}:{host.endpoint.port}")
        else:
            parts.append(host.endpoint.hostname)
    if host.authentication.user:
        parts.append(f"user={host.authentication.user}")
    if host.authentication.identity_file:
        parts.append(f"id={host.authentication.identity_file}")
    return ", ".join(parts) if parts else "-"


def selection_summary(selection: SelectedHostState | None) -> str:
    if selection is None:
        return "-"
    parts = [selection.server_name]
    if selection.endpoint_name is not None:
        parts.append(f"endpoint={selection.endpoint_name}")
    if selection.authentication_name is not None:
        parts.append(f"auth={selection.authentication_name}")
    return ", ".join(parts)


def render_endpoint_table(endpoints: list[RemoteEndpointOption]) -> Table:
    table = Table(show_header=True, header_style="bold")
    table.add_column("Name")
    table.add_column("HostName")
    table.add_column("Port")
    table.add_column("Comment")
    for endpoint in endpoints:
        table.add_row(
            endpoint.name or "",
            endpoint.hostname or "",
            str(endpoint.port or ""),
            endpoint.comment or "",
        )
    return table


def render_auth_table(auths: list[RemoteAuthenticationOption]) -> Table:
    table = Table(show_header=True, header_style="bold")
    table.add_column("Name")
    table.add_column("User")
    table.add_column("IdentityFile")
    table.add_column("Comment")
    for auth in auths:
        table.add_row(
            auth.name or "",
            auth.user or "",
            auth.identity_file or "",
            auth.comment or "",
        )
    return table


def emit_validation_result(
    result: ValidationResult,
    *,
    json_output: bool,
    success_message: str = "Validation passed.",
) -> None:
    if json_output:
        typer.echo(json.dumps(result.to_dict(), indent=2))
    else:
        for warning in result.warnings:
            typer.echo(f"WARNING: {warning}", err=True)
        if result.ok:
            typer.echo(success_message)
        else:
            for error in result.errors:
                typer.echo(f"ERROR: {error}", err=True)
    if not result.ok:
        raise typer.Exit(code=1)


def emit_render_result(render_result: RenderResult, *, json_output: bool) -> None:
    if json_output:
        typer.echo(json.dumps(render_result.to_dict(), indent=2))
        return

    for warning in render_result.warnings:
        typer.echo(f"WARNING: {warning}", err=True)
    if render_result.planned_key_copies:
        typer.echo(f"Planned key copies: {len(render_result.planned_key_copies)}", err=True)
    if render_result.planned_key_deletes:
        typer.echo(f"Planned key deletions: {len(render_result.planned_key_deletes)}", err=True)
    typer.echo(render_result.content)

