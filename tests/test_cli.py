from __future__ import annotations

from typer.testing import CliRunner

from ssh_manager.cli import app
from ssh_manager.version import __version__


RUNNER = CliRunner()


def test_root_command_without_args_shows_help() -> None:
    result = RUNNER.invoke(app, [])

    assert result.exit_code == 0
    assert "Usage:" in result.output
    assert "add" in result.output
    assert "local" in result.output
    assert "remote" in result.output


def test_version_option_returns_single_source_version() -> None:
    result = RUNNER.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert result.output.strip() == __version__


def test_local_group_without_subcommand_shows_help() -> None:
    result = RUNNER.invoke(app, ["local"])

    assert result.exit_code == 0
    assert "Usage:" in result.output
    assert "Inspect local ssh config" in result.output
    assert "list" in result.output


def test_remote_group_without_subcommand_shows_help() -> None:
    result = RUNNER.invoke(app, ["remote"])

    assert result.exit_code == 0
    assert "Usage:" in result.output
    assert "Inspect remote repo configs" in result.output
    assert "list" in result.output
    assert "show" in result.output
