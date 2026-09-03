from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from typer.testing import CliRunner

from keywharf.cli import app
from keywharf.version import __version__

RUNNER = CliRunner()


def test_root_without_command_exits_successfully() -> None:
    result = RUNNER.invoke(app, [])

    assert result.exit_code == 0


def test_version_option_returns_single_source_version() -> None:
    result = RUNNER.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert result.output.strip() == __version__


def test_init_without_required_workspace_name_reports_missing_argument() -> None:
    result = RUNNER.invoke(app, ["init"])

    assert result.exit_code == 2


def test_main_exits_cleanly_for_keywharf_errors(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir(parents=True)

    env = os.environ.copy()
    pythonpath = str(repo_root / "src")
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = os.pathsep.join(path for path in (pythonpath, existing_pythonpath) if path)

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
