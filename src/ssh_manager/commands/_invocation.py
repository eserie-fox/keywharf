"""Canonical CLI invocation helpers for retry hints and sudo re-exec."""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import shlex
import sys
from typing import Any, Mapping

import click
from click.core import ParameterSource


_AUTO_EXCLUDED_PARAMETER_NAMES = {"install_completion", "show_completion"}
_DEFAULT_PARAMETER_SOURCES = {None, ParameterSource.DEFAULT, ParameterSource.DEFAULT_MAP}


@dataclass(slots=True)
class CommandInvocation:
    """Stable, canonical argv for the current command."""

    argv: list[str]

    def display(self) -> str:
        return shlex.join(["ssh-manager", *self.argv])

    def with_sudo_flag(self) -> "CommandInvocation":
        if "--sudo" in self.argv:
            return CommandInvocation([*self.argv])
        return CommandInvocation([*self.argv, "--sudo"])

    def sudo_exec_args(self) -> list[str]:
        cli_path = Path(sys.executable).resolve().with_name("ssh-manager")
        sudo_argv = self.with_sudo_flag().argv
        if cli_path.exists() and os.access(cli_path, os.X_OK):
            return ["sudo", str(cli_path), *sudo_argv]
        return ["sudo", sys.executable, "-m", "ssh_manager", *sudo_argv]


def build_command_invocation(
    ctx: click.Context,
    *,
    overrides: Mapping[str, Any] | None = None,
    exclude: tuple[str, ...] = ("sudo",),
) -> CommandInvocation:
    """Build one canonical argv for the current Click/Typer command context."""

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


def _context_chain(ctx: click.Context) -> list[click.Context]:
    chain: list[click.Context] = []
    current: click.Context | None = ctx
    while current is not None:
        chain.append(current)
        current = current.parent
    chain.reverse()
    return chain


def _serialize_context_params(
    ctx: click.Context,
    *,
    excluded_names: set[str],
    overrides: Mapping[str, Any],
) -> list[str]:
    argv: list[str] = []
    for parameter in ctx.command.params:
        if not parameter.expose_value:
            continue
        name = parameter.name
        if name is None or name in excluded_names:
            continue
        value = overrides[name] if name in overrides else ctx.params.get(name)
        if isinstance(parameter, click.Argument):
            argv.extend(_serialize_argument(value))
            continue
        if name not in overrides and ctx.get_parameter_source(name) in _DEFAULT_PARAMETER_SOURCES:
            continue
        argv.extend(_serialize_option(parameter, value))
    return argv


def _serialize_argument(value: Any) -> list[str]:
    return [_serialize_scalar(item) for item in _iter_values(value)]


def _serialize_option(parameter: click.Option, value: Any) -> list[str]:
    if value is None:
        return []

    if parameter.is_bool_flag:
        if value:
            return [parameter.opts[0]]
        if parameter.secondary_opts:
            return [parameter.secondary_opts[0]]
        return []

    if parameter.multiple:
        argv: list[str] = []
        for item in _iter_values(value):
            argv.append(parameter.opts[0])
            argv.extend(_serialize_composite_value(item))
        return argv

    return [parameter.opts[0], *_serialize_composite_value(value)]


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

