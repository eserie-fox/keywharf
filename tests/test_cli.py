from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

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
    assert "list" in result.output
    assert "show" in result.output


def test_version_option_returns_single_source_version() -> None:
    result = RUNNER.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert result.output.strip() == __version__


def test_local_group_without_subcommand_shows_help() -> None:
    result = RUNNER.invoke(app, ["local"])

    assert "Inspect local desired state" in result.output
    assert "list" in result.output
    assert "show" in result.output


def test_repo_group_without_subcommand_shows_help() -> None:
    result = RUNNER.invoke(app, ["repo"])

    assert "workspace host repo" in result.output
    assert "init" in result.output
    assert "sync" in result.output
    assert "host" in result.output


def test_repo_host_group_without_subcommand_shows_help() -> None:
    result = RUNNER.invoke(app, ["repo", "host"])

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

    assert "Manage named endpoint options for one host." in result.output
    assert "list" in result.output
    assert "show" in result.output
    assert "add" in result.output
    assert "update" in result.output
    assert "remove" in result.output


def test_repo_host_auth_group_without_subcommand_shows_help() -> None:
    result = RUNNER.invoke(app, ["repo", "host", "auth"])

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


def test_main_exits_cleanly_for_keywharf_errors(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir(parents=True)

    env = os.environ.copy()
    pythonpath = str(repo_root / "src")
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        f"{pythonpath}:{existing_pythonpath}"
        if existing_pythonpath
        else pythonpath
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "keywharf.cli",
            "--workspace",
            str(workspace_root),
            "select",
            "demo",
        ],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2
    assert "Config file not found at" in result.stderr
    assert "Traceback" not in result.stderr
    assert "click.exceptions.Exit" not in result.stderr
    assert "Traceback" not in result.stdout
    assert "click.exceptions.Exit" not in result.stdout
