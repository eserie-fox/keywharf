from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from keywharf.cli import app
from keywharf.commands._invocation import CommandInvocation
from keywharf.commands._privilege import raise_for_missing_privileges
from keywharf.domain.errors import PrivilegeRequiredError
from keywharf.services.repo_sync import analyze_host_repo_sync_root_requirements
from tests.support import make_workspace, write_manager_config


RUNNER = CliRunner()


def test_raise_for_missing_privileges_includes_retry_hint() -> None:
    invocation = CommandInvocation(["select", "demo"])

    with pytest.raises(PrivilegeRequiredError) as exc:
        raise_for_missing_privileges(
            operation="select",
            reasons=["state file path is not writable by current user: /root/state.json"],
            invocation=invocation,
            subject="the state file",
        )

    message = str(exc.value)
    assert "select requires elevated privileges" in message
    assert "Retry with: keywharf select demo --sudo" in message


def test_select_with_sudo_reexecs_full_command(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class ReexecCalled(RuntimeError):
        pass

    def fake_execvp(program: str, args: list[str]) -> None:
        captured["program"] = program
        captured["args"] = args
        raise ReexecCalled("reexec")

    monkeypatch.setattr("keywharf.commands._privilege.current_user_is_root", lambda: False)
    monkeypatch.setattr("keywharf.commands._privilege.shutil.which", lambda name: "/usr/bin/sudo")
    monkeypatch.setattr("keywharf.commands._privilege.os.execvp", fake_execvp)

    result = RUNNER.invoke(app, ["select", "demo", "--sudo"])

    assert isinstance(result.exception, ReexecCalled)
    assert captured["program"] == "sudo"
    assert "--sudo" in captured["args"]
    assert "select" in captured["args"]
    assert "demo" in captured["args"]


def test_repo_sync_analyzer_reports_unwritable_host_repo_parent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    workspace_root = make_workspace(tmp_path)
    config_path = write_manager_config(
        workspace_root / "config.json",
        host_repo_remote_url="git@example.com:org/hosts.git",
    )
    from tests.support import load_config

    config = load_config(config_path, workspace_root=workspace_root)
    monkeypatch.setattr("keywharf.services.repo_sync.can_write_directory", lambda path: False)
    monkeypatch.setattr("keywharf.services.repo_sync.root_owned_hint", lambda path: "")

    reasons = analyze_host_repo_sync_root_requirements(config)

    assert reasons
    assert "host repo parent is not writable" in reasons[0]


def test_select_succeeds_without_sudo_in_normal_user_paths(tmp_path: Path) -> None:
    from tests.support import host_repo_payload, write_host_repo_config, write_identity_file

    workspace_root = make_workspace(tmp_path)
    config_path = write_manager_config(workspace_root / "config.json")
    host_repo_path = workspace_root / "repo"
    write_identity_file(host_repo_path)
    write_host_repo_config(host_repo_path, payload=host_repo_payload(endpoint_name="public", auth_name="home"))

    result = RUNNER.invoke(
        app,
        ["--config", str(config_path), "select", "demo", "--endpoint", "public", "--auth", "home"],
    )

    assert result.exit_code == 0, result.output
