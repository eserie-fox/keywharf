from __future__ import annotations

from typer.testing import CliRunner

from ssh_manager.cli import app
from ssh_manager.version import __version__


RUNNER = CliRunner()


def test_root_help_shows_final_command_set() -> None:
    result = RUNNER.invoke(app, [])

    assert result.exit_code == 0
    assert "init" in result.output
    assert "pull" in result.output
    assert "validate" in result.output
    assert "render" in result.output
    assert "apply" in result.output
    assert "install-include" in result.output
    assert "select" in result.output
    assert "deselect" in result.output
    assert "local" in result.output
    assert "remote" in result.output


def test_version_option_returns_single_source_version() -> None:
    result = RUNNER.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert result.output.strip() == __version__


def test_removed_legacy_commands_are_absent() -> None:
    for name in ["add", "remove", "flush", "check"]:
        result = RUNNER.invoke(app, [name])
        assert result.exit_code != 0
        assert "No such command" in result.output


def test_local_group_without_subcommand_shows_help() -> None:
    result = RUNNER.invoke(app, ["local"])

    assert result.exit_code == 0
    assert "Inspect local desired state" in result.output
    assert "list" in result.output
    assert "show" in result.output


def test_remote_group_without_subcommand_shows_help() -> None:
    result = RUNNER.invoke(app, ["remote"])

    assert result.exit_code == 0
    assert "stable selectors" in result.output
    assert "list" in result.output
    assert "show" in result.output

