"""Top-level lifecycle, state, apply, and compatibility commands."""

from __future__ import annotations

from collections.abc import Callable
import json
from pathlib import Path

import typer
from rich.console import Console

from ssh_manager.commands.context import (
    get_cli_state,
    get_manager_config,
    get_remote_hosts,
    set_remote_hosts,
)
from ssh_manager.commands.output import render_auth_table, render_endpoint_table
from ssh_manager.domain.errors import SSHManagerError
from ssh_manager.domain.models import SelectedHostState
from ssh_manager.domain.results import RenderResult, ValidationResult
from ssh_manager.services.apply import apply_selected_state
from ssh_manager.services.init import initialize_workspace
from ssh_manager.services.install_include import install_managed_include
from ssh_manager.services.pull import pull_remote_repo
from ssh_manager.services.remote_hosts import (
    build_remote_host_config,
    load_remote_host_map,
)
from ssh_manager.services.render import render_selected_state
from ssh_manager.services.selections import deselect_host, select_host
from ssh_manager.services.validate import validate_workspace
from ssh_manager.storage.state_store import load_state


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
            f"Multiple {label.lower()} options for '{config_name}'. Use --endpoint/--auth or run "
            f"'ssh-manager remote show {config_name}' to inspect stable choices.",
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


def _emit_validation_result(
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


def _emit_render_result(render_result: RenderResult, *, json_output: bool) -> None:
    if json_output:
        typer.echo(json.dumps(render_result.to_dict(), indent=2))
        return

    for warning in render_result.warnings:
        typer.echo(f"WARNING: {warning}", err=True)
    if render_result.planned_key_copies:
        typer.echo(
            f"Planned key copies: {len(render_result.planned_key_copies)}",
            err=True,
        )
    if render_result.planned_key_deletes:
        typer.echo(
            f"Planned key deletions: {len(render_result.planned_key_deletes)}",
            err=True,
        )
    typer.echo(render_result.content)


def _selection_from_indices(
    server_name: str,
    *,
    endpoint_name: str | None,
    authentication_name: str | None,
) -> SelectedHostState:
    return SelectedHostState(
        server_name=server_name,
        endpoint_name=endpoint_name,
        authentication_name=authentication_name,
    )


def _resolve_selected_server_name(config, name_or_index: str) -> str:
    state = load_state(config)
    for selection in state.selected_hosts:
        if selection.server_name == name_or_index:
            return selection.server_name
    try:
        index = int(name_or_index)
    except ValueError as exc:
        raise SSHManagerError(
            f"No selected host named/indexed '{name_or_index}' found in local state."
        ) from exc

    if index < 0 or index >= len(state.selected_hosts):
        raise SSHManagerError(
            f"No selected host named/indexed '{name_or_index}' found in local state."
        )
    return state.selected_hosts[index].server_name


def init(
    ctx: typer.Context,
    data_root: Path | None = typer.Option(
        None,
        "--data-root",
        help="Target data root to initialize (defaults to current directory, or --config parent when --config is absolute).",
        file_okay=False,
        dir_okay=True,
    ),
    ssh_key_remote_repo: str = typer.Option(
        "git@example.com:org/keys.git",
        "--ssh-key-remote-repo",
        help="Remote repo URL placeholder to write into the generated config.",
    ),
    ssh_dir: str = typer.Option(
        "~/.ssh",
        "--ssh-dir",
        help="SSH directory to write into the generated config template.",
    ),
) -> None:
    cli_state = get_cli_state(ctx)
    result = initialize_workspace(
        cli_state.config_override,
        data_root=data_root,
        ssh_key_remote_repo=ssh_key_remote_repo,
        ssh_dir=ssh_dir,
    )
    typer.echo(f"Initialized data root at {result.data_root}.")
    typer.echo(f"Config: {result.config_path}")
    typer.echo(f"State: {result.state_path}")


def pull(ctx: typer.Context) -> None:
    config = get_manager_config(ctx)
    pull_remote_repo(config)
    set_remote_hosts(ctx, load_remote_host_map(config))
    typer.echo("Pulled remote ssh key repository.")


def validate(
    ctx: typer.Context,
    json_output: bool = typer.Option(False, "--json", help="Output JSON for scripting."),
) -> None:
    result = validate_workspace(get_manager_config(ctx))
    _emit_validation_result(result, json_output=json_output)


def render(
    ctx: typer.Context,
    json_output: bool = typer.Option(False, "--json", help="Output JSON for scripting."),
) -> None:
    _emit_render_result(render_selected_state(get_manager_config(ctx)), json_output=json_output)


def apply(
    ctx: typer.Context,
    backup: bool = typer.Option(
        True,
        "--backup/--no-backup",
        help="Create timestamped backup before replacing the managed config fragment.",
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview without writing files."),
    allow_empty: bool = typer.Option(
        False,
        "--allow-empty",
        help="Allow apply to clear a non-empty managed config when local state is empty.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Output JSON for scripting."),
) -> None:
    result = apply_selected_state(
        get_manager_config(ctx),
        backup=backup,
        dry_run=dry_run,
        allow_empty=allow_empty,
    )
    if json_output:
        typer.echo(json.dumps(result.to_dict(), indent=2))
        return

    if dry_run:
        _emit_render_result(result.render_result, json_output=False)
        typer.echo("Dry run: no files were written.", err=True)
        return

    for warning in result.warnings:
        typer.echo(f"WARNING: {warning}", err=True)
    typer.echo(f"Applied managed config at {result.managed_config_path}.")
    if result.copied_keys:
        typer.echo(f"Copied keys: {len(result.copied_keys)}")
    if result.deleted_keys:
        typer.echo(f"Deleted stale keys: {len(result.deleted_keys)}")


def select(
    ctx: typer.Context,
    server_name: str = typer.Argument(..., help="Remote host name to select."),
    endpoint: str | None = typer.Option(
        None,
        "--endpoint",
        help="Stable EndPointName to select. Omit only when the remote config has a single endpoint.",
    ),
    auth: str | None = typer.Option(
        None,
        "--auth",
        help="Stable AuthenticationName to select. Omit only when the remote config has a single authentication option.",
    ),
) -> None:
    config = get_manager_config(ctx)
    remote_hosts = get_remote_hosts(ctx)
    _, selection = select_host(
        config,
        remote_hosts,
        server_name=server_name,
        endpoint_name=endpoint,
        authentication_name=auth,
    )
    typer.echo(
        f"Selected '{selection.server_name}' in local state. "
        "Run 'ssh-manager apply' to materialize the managed config."
    )


def deselect(
    ctx: typer.Context,
    server_name: str = typer.Argument(..., help="Selected host name to remove from local state."),
) -> None:
    _, selection = deselect_host(
        get_manager_config(ctx),
        server_name=server_name,
    )
    typer.echo(
        f"Deselected '{selection.server_name}' from local state. "
        "Run 'ssh-manager apply' to materialize the managed config."
    )


def install_include(
    ctx: typer.Context,
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview without writing files."),
) -> None:
    """Install a minimal Include for the ssh-manager managed config fragment."""

    config = get_manager_config(ctx)
    result = install_managed_include(config, dry_run=dry_run)
    if result.already_present:
        typer.echo(f"Include already present in {result.main_config_path}.")
        return
    if dry_run:
        console.print(
            f"Dry run: would update {result.main_config_path} with `{result.include_line}`."
        )
        console.print(result.rendered_content)
        return
    typer.echo(
        f"Installed Include into {result.main_config_path} for {result.managed_config_path}."
    )


def add(
    ctx: typer.Context,
    config_name: str = typer.Argument(..., help="Compatibility alias for 'select'."),
    endpoint_id: int | None = typer.Option(
        None,
        "--endpoint-id",
        help="Compatibility selector: endpoint index to use (prefer --endpoint with 'select').",
    ),
    auth_id: int | None = typer.Option(
        None,
        "--auth-id",
        help="Compatibility selector: authentication index to use (prefer --auth with 'select').",
    ),
    non_interactive: bool = typer.Option(
        False,
        "--non-interactive",
        help="Fail instead of prompting when multiple choices exist.",
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview without writing state."),
) -> None:
    remote_hosts = get_remote_hosts(ctx)
    remote_host = remote_hosts.get(config_name)
    if remote_host is None:
        raise SSHManagerError(
            f"Config '{config_name}' not found in remote repo. Run 'ssh-manager remote list' to see available names."
        )

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
    selection = _selection_from_indices(
        config_name,
        endpoint_name=remote_host.endpoints[selected_endpoint].name,
        authentication_name=remote_host.authentication[selected_auth].name,
    )

    if dry_run:
        preview = build_remote_host_config(
            get_manager_config(ctx),
            remote_hosts,
            server_name=config_name,
            endpoint_id=selected_endpoint,
            auth_id=selected_auth,
        )
        typer.echo("Compatibility alias preview for 'select':")
        typer.echo(json.dumps(selection.to_dict(), indent=2))
        typer.echo(preview.to_string(0))
        return

    select_host(
        get_manager_config(ctx),
        remote_hosts,
        server_name=selection.server_name,
        endpoint_name=selection.endpoint_name,
        authentication_name=selection.authentication_name,
    )
    typer.echo(
        f"Compatibility alias: selected '{selection.server_name}' in local state. "
        "Prefer 'ssh-manager select', then run 'ssh-manager apply' to materialize changes."
    )


def remove(
    ctx: typer.Context,
    name_or_index: str = typer.Argument(..., help="Compatibility alias for 'deselect'."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview without writing state."),
) -> None:
    config = get_manager_config(ctx)
    server_name = _resolve_selected_server_name(config, name_or_index)
    if not yes and not typer.confirm(
        f"Remove '{server_name}' from local state?",
        default=False,
    ):
        typer.echo("Canceled.")
        return

    if dry_run:
        typer.echo(
            f"Compatibility alias dry run: would deselect '{server_name}'. "
            "Prefer 'ssh-manager deselect'."
        )
        return

    deselect_host(config, server_name=server_name)
    typer.echo(
        f"Compatibility alias: deselected '{server_name}' from local state. "
        "Prefer 'ssh-manager deselect', then run 'ssh-manager apply' to materialize changes."
    )


def flush(
    ctx: typer.Context,
    backup: bool = typer.Option(
        True,
        "--backup/--no-backup",
        help="Compatibility alias for 'apply'.",
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview without writing files."),
    allow_empty: bool = typer.Option(
        False,
        "--allow-empty",
        help="Allow clearing a non-empty managed config when local state is empty.",
    ),
) -> None:
    result = apply_selected_state(
        get_manager_config(ctx),
        backup=backup,
        dry_run=dry_run,
        allow_empty=allow_empty,
    )
    if dry_run:
        _emit_render_result(result.render_result, json_output=False)
        typer.echo(
            "Compatibility alias dry run for 'apply'. Prefer 'ssh-manager render' or 'ssh-manager apply --dry-run'.",
            err=True,
        )
        return

    typer.echo(
        f"Compatibility alias: applied managed config at {result.managed_config_path}. "
        "Prefer 'ssh-manager apply'."
    )


def check(
    ctx: typer.Context,
    json_output: bool = typer.Option(False, "--json", help="Output JSON for scripting."),
) -> None:
    result = validate_workspace(get_manager_config(ctx))
    _emit_validation_result(
        result,
        json_output=json_output,
        success_message="Compatibility alias for 'validate'. Prefer 'ssh-manager validate'.",
    )


def register(app: typer.Typer) -> None:
    app.command("init", help="Initialize a minimal data-root/config/state skeleton.")(init)
    app.command("pull", help="Clone or sync the remote repository.")(pull)
    app.command("validate", help="Validate config, remote definitions, local state, and selector stability.")(validate)
    app.command("render", help="Render the desired managed SSH config preview without writing files.")(render)
    app.command("apply", help="Validate, render, sync managed keys, and atomically replace the managed config.")(apply)
    app.command("select", help="Select one remote host choice into local desired state.")(select)
    app.command("deselect", help="Remove one selected host from local desired state.")(deselect)
    app.command("install-include", help="Install a minimal Include for the manager-owned config fragment.")(install_include)
    app.command(
        "add",
        help="Compatibility alias for 'select'. It updates local state only; prefer 'select'.",
    )(add)
    app.command(
        "remove",
        help="Compatibility alias for 'deselect'. It updates local state only; prefer 'deselect'.",
    )(remove)
    app.command(
        "flush",
        help="Compatibility alias for 'apply'. It rebuilds manager-owned files from local state; prefer 'apply'.",
    )(flush)
    app.command(
        "check",
        help="Compatibility alias for 'validate'. Prefer 'validate'.",
    )(check)
