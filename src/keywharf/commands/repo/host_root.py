"""Host-level host repo commands."""

from __future__ import annotations

import typer

from keywharf.commands.context import get_manager_config
from keywharf.commands.repo.helpers import (
    reject_option_and_clear_flag,
    run_host_repo_mutation,
)
from keywharf.commands.repo.output import (
    emit_host,
    emit_host_list,
    emit_host_repo_mutation,
)
from keywharf.services.host_editor import (
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
    json_output: bool = typer.Option(False, "--json", help="Output JSON for scripting."),
) -> None:
    """List hosts from the host repo."""

    emit_host_list(list_host_definitions(get_manager_config(ctx)), json_output=json_output)


def show_host_command(
    ctx: typer.Context,
    server_name: str = typer.Argument(..., help="Canonical ServerName to inspect."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON for scripting."),
) -> None:
    """Show one host from the host repo."""

    emit_host(
        get_host_definition(get_manager_config(ctx), server_name),
        json_output=json_output,
    )


def add_host_command(
    ctx: typer.Context,
    server_name: str = typer.Argument(..., help="New canonical ServerName."),
    aliases: list[str] | None = typer.Option(
        None, "--alias", help="Declare a literal SSH alias; repeat to replace the alias set."
    ),
    comment: str | None = typer.Option(None, "--comment", help="Optional host comment."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON for scripting."),
    sudo: bool = typer.Option(
        False, "--sudo", help="Re-exec the full command via sudo when root is required."
    ),
) -> None:
    """Add one host shell to the host repo."""

    result = run_host_repo_mutation(
        ctx,
        command_name="repo host add",
        sudo=sudo,
        action=lambda config: add_host_definition(
            config,
            server_name=server_name,
            comment=comment,
            aliases=aliases or None,
        ),
    )
    if result is not None:
        emit_host_repo_mutation(result, json_output=json_output)


def update_host_command(
    ctx: typer.Context,
    server_name: str = typer.Argument(..., help="Existing canonical ServerName to update."),
    new_name: str | None = typer.Option(
        None,
        "--new-name",
        help="Change canonical ServerName; existing local references are not migrated.",
    ),
    aliases: list[str] | None = typer.Option(
        None, "--alias", help="Declare a literal SSH alias; repeat to replace the alias set."
    ),
    comment: str | None = typer.Option(None, "--comment", help="Replace the host comment."),
    clear_aliases: bool = typer.Option(False, "--clear-aliases", help="Remove all shared aliases."),
    clear_comment: bool = typer.Option(False, "--clear-comment", help="Clear the host comment."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON for scripting."),
    sudo: bool = typer.Option(
        False, "--sudo", help="Re-exec the full command via sudo when root is required."
    ),
) -> None:
    """Update one host shell in the host repo."""

    reject_option_and_clear_flag(
        value=aliases or None,
        clear=clear_aliases,
        option_name="--alias",
        clear_name="--clear-aliases",
    )
    reject_option_and_clear_flag(
        value=comment,
        clear=clear_comment,
        option_name="--comment",
        clear_name="--clear-comment",
    )

    result = run_host_repo_mutation(
        ctx,
        command_name="repo host update",
        sudo=sudo,
        action=lambda config: update_host_definition(
            config,
            server_name=server_name,
            new_name=new_name,
            comment=comment,
            aliases=aliases or None,
            clear_comment=clear_comment,
            clear_aliases=clear_aliases,
        ),
    )
    if result is not None:
        emit_host_repo_mutation(result, json_output=json_output)


def remove_host_command(
    ctx: typer.Context,
    server_name: str = typer.Argument(..., help="Canonical ServerName to remove."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON for scripting."),
    sudo: bool = typer.Option(
        False, "--sudo", help="Re-exec the full command via sudo when root is required."
    ),
) -> None:
    """Remove one host from the host repo."""

    result = run_host_repo_mutation(
        ctx,
        command_name="repo host remove",
        sudo=sudo,
        action=lambda config: remove_host_definition(config, server_name=server_name),
    )
    if result is not None:
        emit_host_repo_mutation(result, json_output=json_output)
