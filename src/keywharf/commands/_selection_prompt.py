"""CLI helpers for completing select command choices."""

from __future__ import annotations

from collections.abc import Callable, Sequence

import click
import typer

from keywharf.domain.errors import KeywharfError
from keywharf.domain.models import (
    HostAuthenticationOption,
    HostDefinition,
    HostEndpointOption,
)


def complete_selection_names(
    host_definitions: dict[str, HostDefinition],
    *,
    server_name: str,
    endpoint_name: str | None,
    authentication_name: str | None,
) -> tuple[str | None, str | None]:
    host_definition = host_definitions.get(server_name)
    if host_definition is None:
        return endpoint_name, authentication_name

    resolved_endpoint = _complete_option_name(
        host_definition.endpoints,
        requested_name=endpoint_name,
        server_name=server_name,
        label="endpoint",
        flag_name="--endpoint",
        formatter=_format_endpoint_choice,
    )
    resolved_auth = _complete_option_name(
        host_definition.authentication,
        requested_name=authentication_name,
        server_name=server_name,
        label="authentication",
        flag_name="--auth",
        formatter=_format_auth_choice,
    )
    return resolved_endpoint, resolved_auth


def _complete_option_name(
    options: Sequence[HostEndpointOption] | Sequence[HostAuthenticationOption],
    *,
    requested_name: str | None,
    server_name: str,
    label: str,
    flag_name: str,
    formatter: Callable[[HostEndpointOption | HostAuthenticationOption], str],
) -> str | None:
    if requested_name is not None or not options:
        return requested_name

    if len(options) == 1:
        return options[0].name

    available_names = [option.name for option in options if option.name is not None]
    if len(available_names) != len(options):
        return requested_name

    if not _supports_interactive_selection():
        available = ", ".join(available_names)
        raise KeywharfError(
            f"Config '{server_name}' has multiple {label} options and interactive selection is unavailable. "
            f"Pass {flag_name} <stable_name>. Available {label} stable names: {available}."
        )

    typer.echo(f"Select {label} for '{server_name}':")
    for index, option in enumerate(options, start=1):
        typer.echo(f"{index}. {formatter(option)}")
    choice = click.prompt(
        f"Enter {label} number",
        type=click.IntRange(1, len(options)),
        show_choices=False,
    )
    return options[choice - 1].name


def _supports_interactive_selection() -> bool:
    return _stream_is_tty("stdin") and _stream_is_tty("stdout")


def _stream_is_tty(name: str) -> bool:
    stream = click.get_text_stream(name)
    isatty = getattr(stream, "isatty", None)
    if isatty is None:
        return False
    try:
        return bool(isatty())
    except OSError:
        return False


def _format_endpoint_choice(option: HostEndpointOption | HostAuthenticationOption) -> str:
    endpoint = _require_endpoint(option)
    parts = [endpoint.name or "-", _format_endpoint_target(endpoint)]
    if endpoint.comment:
        parts.append(endpoint.comment)
    return " | ".join(parts)


def _format_endpoint_target(endpoint: HostEndpointOption) -> str:
    if endpoint.hostname and endpoint.port is not None:
        return f"{endpoint.hostname}:{endpoint.port}"
    if endpoint.hostname:
        return endpoint.hostname
    if endpoint.port is not None:
        return f"port={endpoint.port}"
    return "-"


def _format_auth_choice(option: HostEndpointOption | HostAuthenticationOption) -> str:
    auth = _require_auth(option)
    parts = [
        auth.name or "-",
        f"user={auth.user or '-'}",
        f"identity={auth.identity_file or '-'}",
    ]
    if auth.comment:
        parts.append(auth.comment)
    return " | ".join(parts)


def _require_endpoint(option: HostEndpointOption | HostAuthenticationOption) -> HostEndpointOption:
    if isinstance(option, HostEndpointOption):
        return option
    raise TypeError(f"Expected HostEndpointOption, got {type(option)!r}")


def _require_auth(option: HostEndpointOption | HostAuthenticationOption) -> HostAuthenticationOption:
    if isinstance(option, HostAuthenticationOption):
        return option
    raise TypeError(f"Expected HostAuthenticationOption, got {type(option)!r}")
