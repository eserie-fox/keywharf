from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from ssh_manager.cli import app
from ssh_manager.commands._invocation import CommandInvocation
from ssh_manager.commands._privilege import raise_for_missing_privileges
from ssh_manager.domain.errors import PermissionOperationError
from ssh_manager.services.pull import analyze_pull_root_requirements
from tests.support import make_data_root, write_manager_config


RUNNER = CliRunner()


def test_raise_for_missing_privileges_includes_retry_hint() -> None:
    invocation = CommandInvocation(["select", "demo"])

    with pytest.raises(PermissionOperationError) as exc:
        raise_for_missing_privileges(
            operation="select",
            reasons=["state file path is not writable by current user: /root/state.json"],
            invocation=invocation,
            subject="the state file",
        )

    message = str(exc.value)
    assert "select requires elevated privileges" in message
    assert "Retry with: ssh-manager select demo --sudo" in message


def test_select_with_sudo_reexecs_full_command(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class ReexecCalled(RuntimeError):
        pass

    def fake_execvp(program: str, args: list[str]) -> None:
        captured["program"] = program
        captured["args"] = args
        raise ReexecCalled("reexec")

    monkeypatch.setattr("ssh_manager.commands._privilege.current_user_is_root", lambda: False)
    monkeypatch.setattr("ssh_manager.commands._privilege.shutil.which", lambda name: "/usr/bin/sudo")
    monkeypatch.setattr("ssh_manager.commands._privilege.os.execvp", fake_execvp)

    result = RUNNER.invoke(app, ["select", "demo", "--sudo"])

    assert isinstance(result.exception, ReexecCalled)
    assert captured["program"] == "sudo"
    assert "--sudo" in captured["args"]
    assert "select" in captured["args"]
    assert "demo" in captured["args"]


def test_pull_analyzer_reports_unwritable_repo_parent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    data_root = make_data_root(tmp_path)
    config_path = write_manager_config(data_root / "config.json")
    from tests.support import load_config

    config = load_config(config_path, data_root=data_root)
    monkeypatch.setattr("ssh_manager.services.pull.can_write_directory", lambda path: False)
    monkeypatch.setattr("ssh_manager.services.pull.root_owned_hint", lambda path: "")

    reasons = analyze_pull_root_requirements(config)

    assert reasons
    assert "local repo parent is not writable" in reasons[0]


def test_select_succeeds_without_sudo_in_normal_user_paths(tmp_path: Path) -> None:
    from tests.support import remote_repo_payload, write_identity_file, write_remote_repo_config

    data_root = make_data_root(tmp_path)
    config_path = write_manager_config(data_root / "config.json")
    repo_root = data_root / "repos" / "keys"
    write_identity_file(repo_root)
    write_remote_repo_config(repo_root, payload=remote_repo_payload(endpoint_name="public", auth_name="home"))

    result = RUNNER.invoke(
        app,
        ["--config", str(config_path), "select", "demo", "--endpoint", "public", "--auth", "home"],
    )

    assert result.exit_code == 0, result.output

