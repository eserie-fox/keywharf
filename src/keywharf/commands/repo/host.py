"""Host repo inspection and editing commands."""

from __future__ import annotations

import re

import typer

from keywharf.commands.context import get_manager_config
from keywharf.commands.output import compile_pattern
from keywharf.commands.repo.helpers import run_host_definition_mutation
from keywharf.commands.repo.output import (
    emit_host_definition,
    emit_host_definition_list,
    emit_host_definition_mutation,
)
from keywharf.services.host_definition_editor import (
    add_host_definition,
    get_host_definition,
    list_host_definitions,
    remove_host_definition,
    update_host_definition,
)


def register(app: typer.Typer) -> None:
    app.command("list")(list_host_command)
    app.command("show")(show_host_command)
    app.command("add")(add_host_command)
    app.command("update")(update_host_command)
    app.command("remove")(remove_host_command)


def list_host_command(
    ctx: typer.Context,
    pattern: str | None = typer.Option(
        None,
        "--pattern",
        "-p",
        help="Regex to search host names (re.search).",
    ),
    json_output: bool = typer.Option(False, "--json", help="Output JSON for scripting."),
) -> None:
    """List host definitions from the host repo."""

    try:
        regex = compile_pattern(pattern)
    except re.error as exc:
        raise typer.BadParameter(f"Invalid regex pattern: {exc}") from exc

    hosts = [
        host
        for host in list_host_definitions(get_manager_config(ctx))
        if host.server_name is not None and (regex is None or regex.search(host.server_name))
    ]
    emit_host_definition_list(hosts, json_output=json_output)


def show_host_command(
    ctx: typer.Context,
    server_name: str = typer.Argument(..., help="Host name to inspect."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON for scripting."),
) -> None:
    """Show one host definition from the host repo."""

    emit_host_definition(
        get_host_definition(get_manager_config(ctx), server_name),
        json_output=json_output,
    )


def add_host_command(
    ctx: typer.Context,
    server_name: str = typer.Argument(..., help="New host name."),
    hostname: str = typer.Option(..., "--hostname", help="HostName for the initial endpoint."),
    user: str = typer.Option(..., "--user", help="User for the initial authentication option."),
    identity_file: str = typer.Option(
        ...,
        "--identity-file",
        help="IdentityFile path stored in the host repo config.",
    ),
    port: int = typer.Option(22, "--port", min=1, max=65535, help="Port for the initial endpoint."),
    comment: str | None = typer.Option(None, "--comment", help="Optional host comment."),
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
    """Add one host definition to the host repo."""

    result = run_host_definition_mutation(
        ctx,
        command_name="repo host add",
        sudo=sudo,
        action=lambda config: add_host_definition(
            config,
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
    if result is not None:
        emit_host_definition_mutation(result, json_output=json_output)


def update_host_command(
    ctx: typer.Context,
    server_name: str = typer.Argument(..., help="Existing host name to update."),
    new_name: str | None = typer.Option(None, "--new-name", help="Rename the host."),
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
        help="Rename the target endpoint EndPointName.",
    ),
    auth_name: str | None = typer.Option(
        None,
        "--auth-name",
        help="Rename the target authentication AuthenticationName.",
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
    """Update one host definition in the host repo."""

    result = run_host_definition_mutation(
        ctx,
        command_name="repo host update",
        sudo=sudo,
        action=lambda config: update_host_definition(
            config,
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
    if result is not None:
        emit_host_definition_mutation(result, json_output=json_output)


def remove_host_command(
    ctx: typer.Context,
    server_name: str = typer.Argument(..., help="Host name to remove."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON for scripting."),
    sudo: bool = typer.Option(False, "--sudo", help="Re-exec the full command via sudo when root is required."),
) -> None:
    """Remove one host definition from the host repo."""

    result = run_host_definition_mutation(
        ctx,
        command_name="repo host remove",
        sudo=sudo,
        action=lambda config: remove_host_definition(config, server_name=server_name),
    )
    if result is not None:
        emit_host_definition_mutation(result, json_output=json_output)
