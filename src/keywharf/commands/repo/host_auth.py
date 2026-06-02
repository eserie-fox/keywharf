"""Authentication-level host repo commands."""

from __future__ import annotations

import typer

from keywharf.commands.context import get_manager_config
from keywharf.commands.repo.helpers import (
    reject_option_and_clear_flag,
    run_host_repo_mutation,
)
from keywharf.commands.repo.output import (
    emit_auth,
    emit_auth_list,
    emit_host_repo_mutation,
)
from keywharf.services.host_auth_editor import (
    add_auth_option,
    get_auth_option,
    list_auth_options,
    remove_auth_option,
    update_auth_option,
)


def register(app: typer.Typer) -> None:
    app.command("list")(list_auth_command)
    app.command("show")(show_auth_command)
    app.command("add")(add_auth_command)
    app.command("update")(update_auth_command)
    app.command("remove")(remove_auth_command)


def list_auth_command(
    ctx: typer.Context,
    server_name: str = typer.Argument(..., help="Host name to inspect."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON for scripting."),
) -> None:
    """List authentication options for one host."""

    emit_auth_list(
        server_name,
        list_auth_options(get_manager_config(ctx), server_name),
        json_output=json_output,
    )


def show_auth_command(
    ctx: typer.Context,
    server_name: str = typer.Argument(..., help="Host name to inspect."),
    auth_name: str = typer.Argument(..., help="Authentication name to inspect."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON for scripting."),
) -> None:
    """Show one authentication option for one host."""

    emit_auth(
        server_name,
        get_auth_option(
            get_manager_config(ctx),
            server_name=server_name,
            auth_name=auth_name,
        ),
        json_output=json_output,
    )


def add_auth_command(
    ctx: typer.Context,
    server_name: str = typer.Argument(..., help="Host name to update."),
    auth_name: str = typer.Argument(..., help="New authentication name."),
    user: str | None = typer.Option(None, "--user", help="Optional SSH user."),
    identity_file: str | None = typer.Option(
        None,
        "--identity-file",
        help="Optional IdentityFile path stored in the host repo.",
    ),
    comment: str | None = typer.Option(None, "--comment", help="Optional authentication comment."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON for scripting."),
    sudo: bool = typer.Option(
        False, "--sudo", help="Re-exec the full command via sudo when root is required."
    ),
) -> None:
    """Add one named authentication option to one host."""

    result = run_host_repo_mutation(
        ctx,
        command_name="repo host auth add",
        sudo=sudo,
        action=lambda config: add_auth_option(
            config,
            server_name=server_name,
            auth_name=auth_name,
            user=user,
            identity_file=identity_file,
            comment=comment,
        ),
    )
    if result is not None:
        emit_host_repo_mutation(result, json_output=json_output)


def update_auth_command(
    ctx: typer.Context,
    server_name: str = typer.Argument(..., help="Host name to update."),
    auth_name: str = typer.Argument(..., help="Existing authentication name to update."),
    new_name: str | None = typer.Option(
        None, "--new-name", help="Rename the authentication option."
    ),
    user: str | None = typer.Option(None, "--user", help="Replace the SSH user."),
    clear_user: bool = typer.Option(False, "--clear-user", help="Clear the SSH user."),
    identity_file: str | None = typer.Option(
        None,
        "--identity-file",
        help="Replace the IdentityFile path.",
    ),
    clear_identity_file: bool = typer.Option(
        False,
        "--clear-identity-file",
        help="Clear the IdentityFile path.",
    ),
    comment: str | None = typer.Option(
        None, "--comment", help="Replace the authentication comment."
    ),
    clear_comment: bool = typer.Option(
        False, "--clear-comment", help="Clear the authentication comment."
    ),
    json_output: bool = typer.Option(False, "--json", help="Output JSON for scripting."),
    sudo: bool = typer.Option(
        False, "--sudo", help="Re-exec the full command via sudo when root is required."
    ),
) -> None:
    """Update one named authentication option on one host."""

    reject_option_and_clear_flag(
        value=user,
        clear=clear_user,
        option_name="--user",
        clear_name="--clear-user",
    )
    reject_option_and_clear_flag(
        value=identity_file,
        clear=clear_identity_file,
        option_name="--identity-file",
        clear_name="--clear-identity-file",
    )
    reject_option_and_clear_flag(
        value=comment,
        clear=clear_comment,
        option_name="--comment",
        clear_name="--clear-comment",
    )

    result = run_host_repo_mutation(
        ctx,
        command_name="repo host auth update",
        sudo=sudo,
        action=lambda config: update_auth_option(
            config,
            server_name=server_name,
            auth_name=auth_name,
            new_name=new_name,
            user=user,
            clear_user=clear_user,
            identity_file=identity_file,
            clear_identity_file=clear_identity_file,
            comment=comment,
            clear_comment=clear_comment,
        ),
    )
    if result is not None:
        emit_host_repo_mutation(result, json_output=json_output)


def remove_auth_command(
    ctx: typer.Context,
    server_name: str = typer.Argument(..., help="Host name to update."),
    auth_name: str = typer.Argument(..., help="Authentication name to remove."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON for scripting."),
    sudo: bool = typer.Option(
        False, "--sudo", help="Re-exec the full command via sudo when root is required."
    ),
) -> None:
    """Remove one named authentication option from one host."""

    result = run_host_repo_mutation(
        ctx,
        command_name="repo host auth remove",
        sudo=sudo,
        action=lambda config: remove_auth_option(
            config,
            server_name=server_name,
            auth_name=auth_name,
        ),
    )
    if result is not None:
        emit_host_repo_mutation(result, json_output=json_output)
