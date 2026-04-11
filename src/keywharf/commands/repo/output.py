"""Repo command output helpers."""

from __future__ import annotations

import json

import typer
from rich.table import Table

from keywharf.commands.output import console, render_auth_table, render_endpoint_table
from keywharf.domain.models import (
    HostAuthenticationOption,
    HostDefinition,
    HostEndpointOption,
    HostExtraConfig,
)
from keywharf.domain.results import HostRepoMutationResult


def emit_host_list(hosts: list[HostDefinition], *, json_output: bool) -> None:
    if json_output:
        typer.echo(json.dumps([host.to_dict() for host in hosts], indent=2))
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("name")
    table.add_column("comment")
    table.add_column("endpoints", justify="right")
    table.add_column("auth", justify="right")
    for host in hosts:
        table.add_row(
            host.server_name or "",
            host.comment or "",
            str(len(host.endpoints)),
            str(len(host.authentication)),
        )
    console.print(table)


def emit_host(host: HostDefinition, *, json_output: bool) -> None:
    if json_output:
        typer.echo(json.dumps(host.to_dict(), indent=2))
        return

    console.print(f"Host: {host.server_name or ''}")
    console.print(f"Comment: {host.comment or '-'}")
    console.print(render_endpoint_table(host.endpoints))
    console.print(render_auth_table(host.authentication))
    if host.extra_config:
        console.print(render_extra_config_table(host.extra_config))


def emit_endpoint_list(
    server_name: str,
    endpoints: list[HostEndpointOption],
    *,
    json_output: bool,
) -> None:
    if json_output:
        typer.echo(json.dumps([endpoint.to_dict() for endpoint in endpoints], indent=2))
        return

    console.print(f"Endpoints for {server_name}:")
    console.print(render_endpoint_table(endpoints))


def emit_endpoint(
    server_name: str,
    endpoint: HostEndpointOption,
    *,
    json_output: bool,
) -> None:
    if json_output:
        typer.echo(json.dumps(endpoint.to_dict(), indent=2))
        return

    console.print(f"Endpoint '{endpoint.name or ''}' for {server_name}:")
    console.print(render_endpoint_table([endpoint]))


def emit_auth_list(
    server_name: str,
    auth_options: list[HostAuthenticationOption],
    *,
    json_output: bool,
) -> None:
    if json_output:
        typer.echo(json.dumps([auth.to_dict() for auth in auth_options], indent=2))
        return

    console.print(f"Authentication options for {server_name}:")
    console.print(render_auth_table(auth_options))


def emit_auth(
    server_name: str,
    auth: HostAuthenticationOption,
    *,
    json_output: bool,
) -> None:
    if json_output:
        typer.echo(json.dumps(auth.to_dict(), indent=2))
        return

    console.print(f"Authentication '{auth.name or ''}' for {server_name}:")
    console.print(render_auth_table([auth]))


def emit_host_repo_mutation(
    result: HostRepoMutationResult,
    *,
    json_output: bool,
) -> None:
    if json_output:
        typer.echo(json.dumps(result.to_dict(), indent=2))
        return

    subject = result.subject
    name = result.name
    server_name = result.server_name

    if result.changed:
        verb = {
            "add": "Added",
            "update": "Updated",
            "remove": "Removed",
        }.get(result.operation, result.operation.title())
        if subject == "host":
            typer.echo(f"{verb} host '{name}' in {result.config_path}.")
        else:
            typer.echo(f"{verb} {subject} '{name}' for host '{server_name}' in {result.config_path}.")
    else:
        if subject == "host":
            typer.echo(f"No host changes were needed for '{name}'.")
        else:
            typer.echo(f"No {subject} changes were needed for '{name}' on host '{server_name}'.")

    for note in result.notes:
        typer.echo(note)
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
