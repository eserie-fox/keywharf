"""Git repository storage helpers."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from keywharf.domain.errors import KeywharfError


def _build_git_environment(remote_repo: str) -> dict[str, str]:
    env = {
        **os.environ,
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_ASKPASS": "echo",
    }
    if remote_repo.startswith("git@") or remote_repo.startswith("ssh://"):
        env["GIT_SSH_COMMAND"] = "ssh -o StrictHostKeyChecking=accept-new -o BatchMode=yes"
    return env


def clone_or_pull_repository(remote_repo: str, local_repo: Path) -> None:
    if shutil.which("git") is None:
        raise KeywharfError("git is not available in PATH.")

    env = _build_git_environment(remote_repo)

    if local_repo.exists():
        if not local_repo.is_dir():
            raise KeywharfError(f"Local repo path exists but is not a directory: {local_repo}")
        if not (local_repo / ".git").exists():
            if any(local_repo.iterdir()):
                raise KeywharfError(
                    f"Local repo path exists but is not a git repository: {local_repo}"
                )
            shutil.rmtree(local_repo)
            _run_git(["clone", remote_repo, str(local_repo)], env=env, action="clone remote repo")
            return

        current_url = _run_git(
            ["remote", "get-url", "origin"],
            cwd=local_repo,
            env=env,
            action="read git remote",
        ).strip()
        if current_url != remote_repo:
            raise KeywharfError(
                f"Mismatch repo url, local path {local_repo} url={current_url}, remote url={remote_repo}"
            )
        _run_git(
            ["pull", "--ff-only", "origin"],
            cwd=local_repo,
            env=env,
            action="pull remote repo",
        )
        return

    local_repo.parent.mkdir(parents=True, exist_ok=True)
    _run_git(["clone", remote_repo, str(local_repo)], env=env, action="clone remote repo")


def _run_git(
    args: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str],
    action: str,
) -> str:
    process = subprocess.run(
        ["git", *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
    )
    if process.returncode != 0:
        message = process.stderr.strip() or process.stdout.strip() or "unknown git error"
        raise KeywharfError(f"Failed to {action}: {message}")
    return process.stdout
