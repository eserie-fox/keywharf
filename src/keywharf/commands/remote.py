"""Remote repo inspection and host-editing commands."""

from __future__ import annotations

import json
import re

import typer
from rich.table import Table

from keywharf.commands._invocation import build_command_invocation
from keywharf.commands._privilege import maybe_reexec_with_sudo, raise_for_missing_privileges
from keywharf.commands.context import get_manager_config
from keywharf.commands.output import (
    compile_pattern,
    console,
    render_auth_table,
    render_endpoint_table,
)
from keywharf.domain.errors import KeywharfError
from keywharf.domain.results import RemoteHostMutationResult
from keywharf.services.remote_host_editor import (
    add_remote_host,
    analyze_remote_host_write_root_requirements,
    get_remote_host,
    list_remote_hosts,
    remove_remote_host,
    update_remote_host,
)


app = typer.Typer(
    name="remote",
    no_args_is_help=True,
    help="Inspect and edit the local checkout of the remote host repository.",
)
host_app = typer.Typer(
    name="host",
    no_args_is_help=True,
    help="List, show, and edit remote host definitions in the local repo checkout.",
)
app.add_typer(host_app, name="host")


@host_app.command("list")
def list_remote_host(
    ctx: typer.Context,
    pattern: str | None = typer.Option(
        None,
        "--pattern",
        "-p",
        help="Regex to search remote host names (re.search).",
    ),
    json_output: bool = typer.Option(False, "--json", help="Output JSON for scripting."),
) -> None:
    """List remote host definitions from the local repo checkout."""

    try:
        regex = compile_pattern(pattern)
    except re.error as exc:
        raise typer.BadParameter(f"Invalid regex pattern: {exc}") from exc

    hosts = [
        host
        for host in list_remote_hosts(get_manager_config(ctx))
        if host.server_name is not None and (regex is None or regex.search(host.server_name))
    ]

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


@host_app.command("show")
def show_remote_host_command(
    ctx: typer.Context,
    server_name: str = typer.Argument(..., help="Remote host name to inspect."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON for scripting."),
) -> None:
    """Show one remote host definition."""

    host = get_remote_host(get_manager_config(ctx), server_name)
    if json_output:
        typer.echo(json.dumps(host.to_dict(), indent=2))
        return

    console.print(f"Remote host: {server_name}")
    console.print(render_endpoint_table(host.endpoints))
    console.print(render_auth_table(host.authentication))
    if host.extra_config:
        table = Table(show_header=True, header_style="bold")
        table.add_column("Key")
        table.add_column("Value")
        table.add_column("Comment")
        for item in host.extra_config:
            table.add_row(item.key or "", item.value or "", item.comment or "")
        console.print(table)


@host_app.command("add")
def add_remote_host_command(
    ctx: typer.Context,
    server_name: str = typer.Argument(..., help="New remote host name."),
    hostname: str = typer.Option(..., "--hostname", help="HostName for the initial endpoint."),
    user: str = typer.Option(..., "--user", help="User for the initial authentication option."),
    identity_file: str = typer.Option(
        ...,
        "--identity-file",
        help="IdentityFile path stored in the remote repo config.",
    ),
    port: int = typer.Option(22, "--port", min=1, max=65535, help="Port for the initial endpoint."),
    comment: str | None = typer.Option(None, "--comment", help="Optional remote host comment."),
    endpoint_name: str | None = typer.Option(
        None,
        "--endpoint-name",
        help="Optional EndPointName for the initial endpoint.",
    ),
    auth_name: str | None = typer.Option(
        None,
        "--auth-name",
        help="Optional AuthenticationName for the initial authentication option.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Output JSON for scripting."),
    sudo: bool = typer.Option(False, "--sudo", help="Re-exec the full command via sudo when root is required."),
) -> None:
    """Add one remote host definition."""

    _run_remote_host_mutation(
        ctx,
        command_name="remote host add",
        sudo=sudo,
        json_output=json_output,
        action=lambda: add_remote_host(
            get_manager_config(ctx),
            server_name=server_name,
            hostname=hostname,
            user=user,
            identity_file=identity_file,
            port=port,
            comment=comment,
            endpoint_name=endpoint_name,
            auth_name=auth_name,
        ),
    )


@host_app.command("update")
def update_remote_host_command(
    ctx: typer.Context,
    server_name: str = typer.Argument(..., help="Existing remote host name to update."),
    new_name: str | None = typer.Option(None, "--new-name", help="Rename the remote host."),
    comment: str | None = typer.Option(None, "--comment", help="Replace the top-level host comment."),
    hostname: str | None = typer.Option(None, "--hostname", help="Replace the target endpoint HostName."),
    port: int | None = typer.Option(None, "--port", min=1, max=65535, help="Replace the target endpoint Port."),
    user: str | None = typer.Option(None, "--user", help="Replace the target authentication User."),
    identity_file: str | None = typer.Option(
        None,
        "--identity-file",
        help="Replace the target authentication IdentityFile.",
    ),
    endpoint_name: str | None = typer.Option(
        None,
        "--endpoint-name",
        help="Rename the target endpoint's EndPointName.",
    ),
    auth_name: str | None = typer.Option(
        None,
        "--auth-name",
        help="Rename the target authentication's AuthenticationName.",
    ),
    target_endpoint: str | None = typer.Option(
        None,
        "--target-endpoint",
        help="Select which endpoint to edit when multiple endpoints exist.",
    ),
    target_auth: str | None = typer.Option(
        None,
        "--target-auth",
        help="Select which authentication option to edit when multiple options exist.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Output JSON for scripting."),
    sudo: bool = typer.Option(False, "--sudo", help="Re-exec the full command via sudo when root is required."),
) -> None:
    """Update one remote host definition."""

    _run_remote_host_mutation(
        ctx,
        command_name="remote host update",
        sudo=sudo,
        json_output=json_output,
        action=lambda: update_remote_host(
            get_manager_config(ctx),
            server_name=server_name,
            new_name=new_name,
            comment=comment,
            hostname=hostname,
            port=port,
            user=user,
            identity_file=identity_file,
            endpoint_name=endpoint_name,
            auth_name=auth_name,
            target_endpoint=target_endpoint,
            target_auth=target_auth,
        ),
    )


@host_app.command("remove")
def remove_remote_host_command(
    ctx: typer.Context,
    server_name: str = typer.Argument(..., help="Remote host name to remove."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON for scripting."),
    sudo: bool = typer.Option(False, "--sudo", help="Re-exec the full command via sudo when root is required."),
) -> None:
    """Remove one remote host definition."""

    _run_remote_host_mutation(
        ctx,
        command_name="remote host remove",
        sudo=sudo,
        json_output=json_output,
        action=lambda: remove_remote_host(get_manager_config(ctx), server_name=server_name),
    )


def _run_remote_host_mutation(
    ctx: typer.Context,
    *,
    command_name: str,
    sudo: bool,
    json_output: bool,
    action,
) -> None:
    invocation = build_command_invocation(ctx)
    if maybe_reexec_with_sudo(
        operation=command_name,
        sudo_requested=sudo,
        invocation=invocation,
        subject="the local remote repo config",
    ):
        return

    config = get_manager_config(ctx)
    raise_for_missing_privileges(
        operation=command_name,
        reasons=analyze_remote_host_write_root_requirements(config),
        invocation=invocation,
        subject="the local remote repo config",
    )
    result = action()
    _emit_remote_host_mutation(result, json_output=json_output)


def _emit_remote_host_mutation(result: RemoteHostMutationResult, *, json_output: bool) -> None:
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
        typer.echo(f"{verb} remote host '{noun}' in {result.config_path}.")
    else:
        typer.echo(f"No remote host changes were needed for '{noun}'.")
    for warning in result.warnings:
        typer.echo(f"WARNING: {warning}", err=True)
