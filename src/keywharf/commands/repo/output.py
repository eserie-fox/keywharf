"""Repo command output helpers."""

from __future__ import annotations

import json

import typer
from rich.table import Table

from keywharf.commands.output import console, render_auth_table, render_endpoint_table
from keywharf.domain.models import HostDefinition, HostExtraConfig
from keywharf.domain.results import HostDefinitionMutationResult


def emit_host_definition_list(hosts: list[HostDefinition], *, json_output: bool) -> None:
    if json_output:
        typer.echo(json.dumps([host.to_dict() for host in hosts], indent=2))
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("name")
    table.add_column("endpoints", justify="right")
    table.add_column("auth", justify="right")
    for host in hosts:
        table.add_row(
            host.server_name or "",
            str(len(host.endpoints)),
            str(len(host.authentication)),
        )
    console.print(table)


def emit_host_definition(host: HostDefinition, *, json_output: bool) -> None:
    if json_output:
        typer.echo(json.dumps(host.to_dict(), indent=2))
        return

    console.print(f"Host definition: {host.server_name or ''}")
    console.print(render_endpoint_table(host.endpoints))
    console.print(render_auth_table(host.authentication))
    if host.extra_config:
        console.print(render_extra_config_table(host.extra_config))


def emit_host_definition_mutation(
    result: HostDefinitionMutationResult,
    *,
    json_output: bool,
) -> None:
    if json_output:
        typer.echo(json.dumps(result.to_dict(), indent=2))
        return

    noun = result.host.server_name if result.host is not None else (result.removed_name or "host")
    if result.changed:
        verb = {
            "add": "Added",
            "update": "Updated",
            "remove": "Removed",
        }.get(result.operation, result.operation.title())
        typer.echo(f"{verb} host '{noun}' in {result.config_path}.")
    else:
        typer.echo(f"No host definition changes were needed for '{noun}'.")
    for warning in result.warnings:
        typer.echo(f"WARNING: {warning}", err=True)


def render_extra_config_table(extra_config: list[HostExtraConfig]) -> Table:
    table = Table(show_header=True, header_style="bold")
    table.add_column("Key")
    table.add_column("Value")
    table.add_column("Comment")
    for item in extra_config:
        table.add_row(item.key or "", item.value or "", item.comment or "")
    return table
