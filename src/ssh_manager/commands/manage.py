"""Mutating and validation commands."""

from __future__ import annotations

from collections.abc import Callable

import typer
from rich.console import Console

from ssh_manager.commands.context import (
    get_current_hosts,
    get_manager_config,
    get_remote_hosts,
    set_current_hosts,
    set_remote_hosts,
)
from ssh_manager.commands.output import render_auth_table, render_endpoint_table
from ssh_manager.domain.errors import SSHManagerError
from ssh_manager.services.check import validate_remote_repo_config
from ssh_manager.services.operations import (
    add_host as add_host_operation,
    flush_hosts,
    preview_add_host,
    remove_host as remove_host_operation,
    resolve_local_host,
)
from ssh_manager.services.pull import pull_remote_repo
from ssh_manager.services.remote_hosts import load_remote_host_map


console = Console()


def _choose_index(
    label: str,
    count: int,
    *,
    provided: int | None,
    non_interactive: bool,
    config_name: str,
    render_table: Callable[[object], object],
    options: object,
) -> int:
    if count == 0:
        raise SSHManagerError(f"Config '{config_name}' has no {label.lower()} options.")
    if provided is not None:
        if provided < 0 or provided >= count:
            raise typer.BadParameter(
                f"{label} index out of range. Valid range: 0-{count - 1}."
            )
        return provided
    if count == 1:
        return 0
    if non_interactive:
        raise SSHManagerError(
            f"Multiple {label.lower()} options for '{config_name}'. Use --endpoint-id/--auth-id or run "
            f"'ssh-manager remote show {config_name}' to inspect choices.",
            exit_code=2,
        )

    console.print(f"Select {label} for '{config_name}':")
    console.print(render_table(options))
    selection = typer.prompt(f"Enter {label} index", default="0")
    try:
        index = int(selection)
    except ValueError as exc:
        raise typer.BadParameter(f"{label} index must be an integer") from exc
    if index < 0 or index >= count:
        raise typer.BadParameter(f"{label} index out of range. Valid range: 0-{count - 1}.")
    return index


def add(
    ctx: typer.Context,
    config_name: str = typer.Argument(..., help="Remote config name to add locally."),
    endpoint_id: int | None = typer.Option(
        None,
        "--endpoint-id",
        help="Endpoint index to use (see remote show).",
    ),
    auth_id: int | None = typer.Option(
        None,
        "--auth-id",
        help="Authentication index to use (see remote show).",
    ),
    non_interactive: bool = typer.Option(
        False,
        "--non-interactive",
        help="Fail instead of prompting when multiple choices exist.",
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview without writing files."),
) -> None:
    remote_hosts = get_remote_hosts(ctx)
    current_hosts = get_current_hosts(ctx)
    remote_host = remote_hosts.get(config_name)
    if remote_host is None:
        raise SSHManagerError(
            f"Config '{config_name}' not found in remote repo. Run 'ssh-manager remote list' to see available names."
        )
    if any(host.name == config_name for host in current_hosts):
        raise SSHManagerError(f"Config '{config_name}' already exists locally.")

    selected_endpoint = _choose_index(
        "Endpoint",
        len(remote_host.endpoints),
        provided=endpoint_id,
        non_interactive=non_interactive,
        config_name=config_name,
        render_table=render_endpoint_table,
        options=remote_host.endpoints,
    )
    selected_auth = _choose_index(
        "Authentication",
        len(remote_host.authentication),
        provided=auth_id,
        non_interactive=non_interactive,
        config_name=config_name,
        render_table=render_auth_table,
        options=remote_host.authentication,
    )

    config = get_manager_config(ctx)
    preview = preview_add_host(
        config,
        remote_hosts,
        server_name=config_name,
        endpoint_id=selected_endpoint,
        auth_id=selected_auth,
    )
    if dry_run:
        console.print("Dry run: showing generated host block")
        console.print(preview.to_string(0))
        return

    result = add_host_operation(
        config,
        current_hosts,
        remote_hosts,
        server_name=config_name,
        endpoint_id=selected_endpoint,
        auth_id=selected_auth,
    )
    set_current_hosts(ctx, result.hosts)
    typer.echo(f"Added '{result.host.name}' to ssh config.")


def remove(
    ctx: typer.Context,
    name_or_index: str = typer.Argument(..., help="Host name or index to remove."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview without writing files."),
) -> None:
    current_hosts = get_current_hosts(ctx)
    _, target = resolve_local_host(current_hosts, name_or_index)

    if not yes and not typer.confirm(f"Remove '{target.name}' from ssh config?", default=False):
        typer.echo("Canceled.")
        return

    if dry_run:
        typer.echo(f"Dry run: would remove '{target.name}'.")
        return

    result = remove_host_operation(
        get_manager_config(ctx),
        current_hosts,
        name_or_index=name_or_index,
    )
    set_current_hosts(ctx, result.hosts)
    typer.echo(f"Removed '{result.host.name}'.")


def flush(
    ctx: typer.Context,
    backup: bool = typer.Option(
        True,
        "--backup/--no-backup",
        help="Create timestamped backup before replacing ssh config.",
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview without writing files."),
) -> None:
    current_hosts = get_current_hosts(ctx)
    if dry_run:
        typer.echo("Dry run: would rewrite ssh config with current in-memory hosts.")
        return

    flush_hosts(get_manager_config(ctx), current_hosts, backup=backup)
    typer.echo("Flushed ssh config with atomic write.")


def pull(ctx: typer.Context) -> None:
    config = get_manager_config(ctx)
    pull_remote_repo(config)
    remote_hosts = load_remote_host_map(config)
    set_remote_hosts(ctx, remote_hosts)
    typer.echo("Pulled remote ssh key repository.")


def check(ctx: typer.Context) -> None:
    result = validate_remote_repo_config(get_manager_config(ctx))
    if result.ok:
        typer.echo("Remote repository config is valid.")
        return

    for error in result.errors:
        typer.echo(f"- {error}", err=True)
    raise typer.Exit(code=1)


def register(app: typer.Typer) -> None:
    app.command()(add)
    app.command()(remove)
    app.command()(flush)
    app.command()(pull)
    app.command()(check)
