from __future__ import annotations

from typer.testing import CliRunner

from ssh_manager.cli import app
from ssh_manager.version import __version__


RUNNER = CliRunner()


def test_root_command_without_args_shows_new_workflow_help() -> None:
    result = RUNNER.invoke(app, [])

    assert result.exit_code == 0
    assert "Usage:" in result.output
    assert "init" in result.output
    assert "validate" in result.output
    assert "render" in result.output
    assert "apply" in result.output
    assert "select" in result.output
    assert "deselect" in result.output
    assert "install-include" in result.output
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
    assert "Inspect local desired state" in result.output
    assert "list" in result.output
    assert "show" in result.output


def test_remote_group_without_subcommand_shows_help() -> None:
    result = RUNNER.invoke(app, ["remote"])

    assert result.exit_code == 0
    assert "Usage:" in result.output
    assert "stable selectors" in result.output
    assert "list" in result.output
    assert "show" in result.output


def test_compatibility_add_help_mentions_select() -> None:
    result = RUNNER.invoke(app, ["add", "--help"])

    assert result.exit_code == 0
    assert "Compatibility alias for 'select'" in result.output
