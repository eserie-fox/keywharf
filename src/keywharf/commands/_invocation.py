"""Canonical CLI invocation helpers for retry hints and sudo re-exec."""

from __future__ import annotations

import os
import shlex
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

_AUTO_EXCLUDED_PARAMETER_NAMES = {"install_completion", "show_completion"}
_DEFAULT_PARAMETER_SOURCE_NAMES = {None, "DEFAULT", "DEFAULT_MAP"}


@dataclass(slots=True)
class CommandInvocation:
    """Stable, canonical argv for the current command."""

    argv: list[str]

    def display(self) -> str:
        return shlex.join(["keywharf", *self.argv])

    def with_sudo_flag(self) -> CommandInvocation:
        if "--sudo" in self.argv:
            return CommandInvocation([*self.argv])
        return CommandInvocation([*self.argv, "--sudo"])

    def sudo_exec_args(self) -> list[str]:
        cli_path = Path(sys.executable).resolve().with_name("keywharf")
        sudo_argv = self.with_sudo_flag().argv
        if cli_path.exists() and os.access(cli_path, os.X_OK):
            return ["sudo", str(cli_path), *sudo_argv]
        return ["sudo", sys.executable, "-m", "keywharf", *sudo_argv]


def build_command_invocation(
    ctx: Any,
    *,
    overrides: Mapping[str, Any] | None = None,
    exclude: tuple[str, ...] = ("sudo",),
) -> CommandInvocation:
    """Build one canonical argv for the current Typer command context."""

    override_map = dict(overrides or {})
    excluded_names = set(exclude) | _AUTO_EXCLUDED_PARAMETER_NAMES
    argv: list[str] = []
    context_chain = _context_chain(ctx)

    root_ctx = context_chain[0]
    argv.extend(
        _serialize_context_params(root_ctx, excluded_names=excluded_names, overrides=override_map)
    )

    for command_ctx in context_chain[1:]:
        command_name = command_ctx.info_name or command_ctx.command.name
        if command_name:
            argv.append(command_name)
        argv.extend(
            _serialize_context_params(
                command_ctx,
                excluded_names=excluded_names,
                overrides=override_map,
            )
        )

    return CommandInvocation(argv)


def _context_chain(ctx: Any) -> list[Any]:
    chain: list[Any] = []
    current: Any | None = ctx
    while current is not None:
        chain.append(current)
        current = current.parent
    chain.reverse()
    return chain


def _serialize_context_params(
    ctx: Any,
    *,
    excluded_names: set[str],
    overrides: Mapping[str, Any],
) -> list[str]:
    argv: list[str] = []
    for parameter in ctx.command.params:
        if not getattr(parameter, "expose_value", True):
            continue
        name = parameter.name
        if name is None or name in excluded_names:
            continue
        value = overrides[name] if name in overrides else ctx.params.get(name)
        if _is_argument_parameter(parameter):
            argv.extend(_serialize_argument(value))
            continue
        if name not in overrides and _is_default_parameter_source(ctx, name):
            continue
        argv.extend(_serialize_option(parameter, value))
    return argv


def _is_argument_parameter(parameter: Any) -> bool:
    return not _option_tokens(parameter) and not hasattr(parameter, "is_bool_flag")


def _is_default_parameter_source(ctx: Any, name: str) -> bool:
    source = ctx.get_parameter_source(name)
    source_name = getattr(source, "name", source)
    return source_name in _DEFAULT_PARAMETER_SOURCE_NAMES


def _serialize_argument(value: Any) -> list[str]:
    return [_serialize_scalar(item) for item in _iter_values(value)]


def _serialize_option(parameter: Any, value: Any) -> list[str]:
    if value is None:
        return []

    primary_option = _primary_option_token(parameter)

    if getattr(parameter, "is_bool_flag", False):
        if value:
            return [primary_option]
        secondary_options = _option_tokens_from(getattr(parameter, "secondary_opts", ()))
        if secondary_options:
            return [secondary_options[0]]
        return []

    if getattr(parameter, "multiple", False):
        argv: list[str] = []
        for item in _iter_values(value):
            argv.append(primary_option)
            argv.extend(_serialize_composite_value(item))
        return argv

    return [primary_option, *_serialize_composite_value(value)]


def _primary_option_token(parameter: Any) -> str:
    option_tokens = _option_tokens(parameter)
    if not option_tokens:
        raise TypeError(f"Expected an option parameter, got {parameter!r}")
    return option_tokens[0]


def _option_tokens(parameter: Any) -> list[str]:
    return _option_tokens_from(getattr(parameter, "opts", ()))


def _option_tokens_from(values: Any) -> list[str]:
    if values is None:
        return []
    if isinstance(values, str):
        values = [values]
    return [value for value in values if isinstance(value, str) and value.startswith("-")]


def _serialize_composite_value(value: Any) -> list[str]:
    return [_serialize_scalar(item) for item in _iter_values(value)]


def _iter_values(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, list):
        return value
    return [value]


def _serialize_scalar(value: Any) -> str:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Enum):
        return str(value.value)
    return str(value)
