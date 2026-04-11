from __future__ import annotations

from typer.testing import CliRunner

from keywharf.cli import app
from keywharf.version import __version__


RUNNER = CliRunner()


def test_root_help_shows_current_command_set() -> None:
    result = RUNNER.invoke(app, [])

    assert result.exit_code == 0
    assert "--workspace" in result.output
    assert "init" in result.output
    assert "repo" in result.output
    assert "validate" in result.output
    assert "render" in result.output
    assert "apply" in result.output
    assert "install-include" in result.output
    assert "select" in result.output
    assert "deselect" in result.output
    assert "local" in result.output


def test_version_option_returns_single_source_version() -> None:
    result = RUNNER.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert result.output.strip() == __version__


def test_local_group_without_subcommand_shows_help() -> None:
    result = RUNNER.invoke(app, ["local"])

    assert result.exit_code == 0
    assert "Inspect local desired state" in result.output
    assert "list" in result.output
    assert "show" in result.output


def test_repo_group_without_subcommand_shows_help() -> None:
    result = RUNNER.invoke(app, ["repo"])

    assert result.exit_code == 0
    assert "workspace host repo" in result.output
    assert "init" in result.output
    assert "sync" in result.output
    assert "host" in result.output


def test_repo_host_group_without_subcommand_shows_help() -> None:
    result = RUNNER.invoke(app, ["repo", "host"])

    assert result.exit_code == 0
    assert "host shells" in result.output
    assert "endpoint" in result.output
    assert "authentication" in result.output
    assert "list" in result.output
    assert "show" in result.output
    assert "add" in result.output
    assert "update" in result.output
    assert "remove" in result.output
    assert "endpoint" in result.output
    assert "auth" in result.output


def test_repo_host_endpoint_group_without_subcommand_shows_help() -> None:
    result = RUNNER.invoke(app, ["repo", "host", "endpoint"])

    assert result.exit_code == 0
    assert "Manage named endpoint options for one host." in result.output
    assert "list" in result.output
    assert "show" in result.output
    assert "add" in result.output
    assert "update" in result.output
    assert "remove" in result.output


def test_repo_host_auth_group_without_subcommand_shows_help() -> None:
    result = RUNNER.invoke(app, ["repo", "host", "auth"])

    assert result.exit_code == 0
    assert "Manage named authentication options for one host." in result.output
    assert "list" in result.output
    assert "show" in result.output
    assert "add" in result.output
    assert "update" in result.output
    assert "remove" in result.output


def test_init_without_required_workspace_name_reports_missing_argument() -> None:
    result = RUNNER.invoke(app, ["init"])

    assert result.exit_code != 0
    assert "Missing argument" in result.output
