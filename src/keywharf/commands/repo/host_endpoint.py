"""Endpoint-level host repo commands."""

from __future__ import annotations

import typer

from keywharf.commands.context import get_manager_config
from keywharf.commands.repo.helpers import (
    reject_option_and_clear_flag,
    run_host_repo_mutation,
)
from keywharf.commands.repo.output import (
    emit_endpoint,
    emit_endpoint_list,
    emit_host_repo_mutation,
)
from keywharf.services.host_endpoint_editor import (
    add_endpoint,
    get_endpoint,
    list_endpoints,
    remove_endpoint,
    update_endpoint,
)


def register(app: typer.Typer) -> None:
    app.command("list")(list_endpoint_command)
    app.command("show")(show_endpoint_command)
    app.command("add")(add_endpoint_command)
    app.command("update")(update_endpoint_command)
    app.command("remove")(remove_endpoint_command)


def list_endpoint_command(
    ctx: typer.Context,
    server_name: str = typer.Argument(..., help="Host name to inspect."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON for scripting."),
) -> None:
    """List endpoint options for one host."""

    emit_endpoint_list(
        server_name,
        list_endpoints(get_manager_config(ctx), server_name),
        json_output=json_output,
    )


def show_endpoint_command(
    ctx: typer.Context,
    server_name: str = typer.Argument(..., help="Host name to inspect."),
    endpoint_name: str = typer.Argument(..., help="Endpoint name to inspect."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON for scripting."),
) -> None:
    """Show one endpoint option for one host."""

    emit_endpoint(
        server_name,
        get_endpoint(
            get_manager_config(ctx),
            server_name=server_name,
            endpoint_name=endpoint_name,
        ),
        json_output=json_output,
    )


def add_endpoint_command(
    ctx: typer.Context,
    server_name: str = typer.Argument(..., help="Host name to update."),
    endpoint_name: str = typer.Argument(..., help="New endpoint name."),
    hostname: str = typer.Option(..., "--hostname", help="HostName for the endpoint."),
    port: int | None = typer.Option(
        None, "--port", min=1, max=65535, help="Optional endpoint port."
    ),
    comment: str | None = typer.Option(None, "--comment", help="Optional endpoint comment."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON for scripting."),
    sudo: bool = typer.Option(
        False, "--sudo", help="Re-exec the full command via sudo when root is required."
    ),
) -> None:
    """Add one named endpoint option to one host."""

    result = run_host_repo_mutation(
        ctx,
        command_name="repo host endpoint add",
        sudo=sudo,
        action=lambda config: add_endpoint(
            config,
            server_name=server_name,
            endpoint_name=endpoint_name,
            hostname=hostname,
            port=port,
            comment=comment,
        ),
    )
    if result is not None:
        emit_host_repo_mutation(result, json_output=json_output)


def update_endpoint_command(
    ctx: typer.Context,
    server_name: str = typer.Argument(..., help="Host name to update."),
    endpoint_name: str = typer.Argument(..., help="Existing endpoint name to update."),
    new_name: str | None = typer.Option(None, "--new-name", help="Rename the endpoint."),
    hostname: str | None = typer.Option(None, "--hostname", help="Replace the endpoint HostName."),
    port: int | None = typer.Option(
        None, "--port", min=1, max=65535, help="Replace the endpoint port."
    ),
    clear_port: bool = typer.Option(False, "--clear-port", help="Clear the endpoint port."),
    comment: str | None = typer.Option(None, "--comment", help="Replace the endpoint comment."),
    clear_comment: bool = typer.Option(
        False, "--clear-comment", help="Clear the endpoint comment."
    ),
    json_output: bool = typer.Option(False, "--json", help="Output JSON for scripting."),
    sudo: bool = typer.Option(
        False, "--sudo", help="Re-exec the full command via sudo when root is required."
    ),
) -> None:
    """Update one named endpoint option on one host."""

    reject_option_and_clear_flag(
        value=port,
        clear=clear_port,
        option_name="--port",
        clear_name="--clear-port",
    )
    reject_option_and_clear_flag(
        value=comment,
        clear=clear_comment,
        option_name="--comment",
        clear_name="--clear-comment",
    )

    result = run_host_repo_mutation(
        ctx,
        command_name="repo host endpoint update",
        sudo=sudo,
        action=lambda config: update_endpoint(
            config,
            server_name=server_name,
            endpoint_name=endpoint_name,
            new_name=new_name,
            hostname=hostname,
            port=port,
            clear_port=clear_port,
            comment=comment,
            clear_comment=clear_comment,
        ),
    )
    if result is not None:
        emit_host_repo_mutation(result, json_output=json_output)


def remove_endpoint_command(
    ctx: typer.Context,
    server_name: str = typer.Argument(..., help="Host name to update."),
    endpoint_name: str = typer.Argument(..., help="Endpoint name to remove."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON for scripting."),
    sudo: bool = typer.Option(
        False, "--sudo", help="Re-exec the full command via sudo when root is required."
    ),
) -> None:
    """Remove one named endpoint option from one host."""

    result = run_host_repo_mutation(
        ctx,
        command_name="repo host endpoint remove",
        sudo=sudo,
        action=lambda config: remove_endpoint(
            config,
            server_name=server_name,
            endpoint_name=endpoint_name,
        ),
    )
    if result is not None:
        emit_host_repo_mutation(result, json_output=json_output)
