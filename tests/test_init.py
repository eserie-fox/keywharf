from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from keywharf.cli import app
from tests.support import load_config, read_json

RUNNER = CliRunner()


def test_init_creates_workspace_from_package_resources(tmp_path: Path) -> None:
    ssh_dir = tmp_path / "ssh-home"

    result = RUNNER.invoke(
        app,
        ["init", "demo", "--directory", str(tmp_path), "--ssh-dir", str(ssh_dir)],
    )

    workspace_root = tmp_path / "demo"
    assert result.exit_code == 0, result.output
    assert (workspace_root / "KEYWHARF_WORKSPACE").exists()
    assert (workspace_root / "config.json").exists()
    assert (workspace_root / "state" / "state.json").exists()
    assert (workspace_root / "README.md").exists()
    assert (workspace_root / ".gitignore").exists()
    assert (workspace_root / "repo").is_dir()
    assert not (workspace_root / "repos").exists()
    assert list((workspace_root / "repo").iterdir()) == []
    assert not (workspace_root / "repo" / ".git").exists()

    raw_config = read_json(workspace_root / "config.json")
    assert raw_config["host_repo_remote_url"] is None
    assert raw_config["host_repo_path"] == "%{WORKSPACE}/repo"
    assert raw_config["ssh_dir"] == str(ssh_dir)
    assert raw_config["managed_config_path"] is None
    assert raw_config["managed_keys_dir"] is None

    config = load_config(workspace_root / "config.json", workspace_root=workspace_root)
    assert config.host_repo_path == (workspace_root / "repo").resolve()
    assert config.host_repo_path.exists()
    assert not config.managed_config_path.parent.exists()
    assert not config.managed_keys_dir.exists()
    assert read_json(workspace_root / "state" / "state.json") == {
        "version": 1,
        "selected_hosts": [],
    }

    assert f"Created workspace: {workspace_root.resolve()}" in result.output
    assert str((workspace_root / "KEYWHARF_WORKSPACE").resolve()) in result.output
    assert str((workspace_root / "repo").resolve()) in result.output
    assert "host_repo_remote_url" in result.output
    assert "empty workspace repo" in result.output
    assert "repo sync" in result.output
    assert "repo init" in result.output
    assert "repo host add <server>" in result.output
    assert "repo host endpoint add <server> <endpoint_name> --hostname <host>" in result.output
    assert "repo host auth add <server> <auth_name>" in result.output


def test_init_creates_named_workspace_not_current_directory(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    result = RUNNER.invoke(app, ["init", "demo"])

    assert result.exit_code == 0, result.output
    assert not (tmp_path / "config.json").exists()
    assert not (tmp_path / "state").exists()
    assert (tmp_path / "demo" / "config.json").exists()
    assert (tmp_path / "demo" / "state" / "state.json").exists()
    assert (tmp_path / "demo" / "repo").is_dir()


def test_init_rejects_workspace_option(tmp_path: Path) -> None:
    result = RUNNER.invoke(
        app,
        ["--workspace", str(tmp_path / "demo"), "init", "demo"],
    )

    assert result.exit_code == 1
    assert result.exception is not None
    assert "`keywharf init` does not accept --workspace" in str(result.exception)


def test_init_fails_when_target_exists_and_is_not_empty(tmp_path: Path) -> None:
    workspace_root = tmp_path / "demo"
    workspace_root.mkdir()
    (workspace_root / "existing.txt").write_text("occupied\n", encoding="utf-8")

    result = RUNNER.invoke(app, ["init", "demo", "--directory", str(tmp_path)])

    assert result.exit_code == 1
    assert result.exception is not None
    assert "already exists and is not empty" in str(result.exception)
    assert not (workspace_root / "KEYWHARF_WORKSPACE").exists()
