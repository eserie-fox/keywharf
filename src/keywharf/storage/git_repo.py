"""Git repository storage helpers."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from keywharf.domain.errors import KeywharfError
from keywharf.storage.host_repo import HOST_REPO_CONFIG_FILENAME


def _build_git_environment(remote_url: str) -> dict[str, str]:
    env = {
        **os.environ,
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_ASKPASS": "echo",
    }
    if remote_url.startswith("git@") or remote_url.startswith("ssh://"):
        env["GIT_SSH_COMMAND"] = "ssh -o StrictHostKeyChecking=accept-new -o BatchMode=yes"
    return env


def clone_or_sync_repository(remote_url: str, local_path: Path) -> None:
    if shutil.which("git") is None:
        raise KeywharfError("git is not available in PATH.")

    env = _build_git_environment(remote_url)

    if local_path.exists():
        if not local_path.is_dir():
            raise KeywharfError(f"Host repo path exists but is not a directory: {local_path}")
        if not (local_path / ".git").exists():
            if not any(local_path.iterdir()):
                _run_git(["clone", remote_url, str(local_path)], env=env, action="clone host repo")
                return
            bootstrap_hint = ""
            if (local_path / HOST_REPO_CONFIG_FILENAME).exists():
                bootstrap_hint = (
                    " This looks like a local-first bootstrap created by "
                    "'keywharf repo init'. Initialize git and add a remote yourself, "
                    "or remove this directory before running 'keywharf repo sync'."
                )
            raise KeywharfError(
                f"Host repo path exists but is not a git repository: {local_path}.{bootstrap_hint}"
            )

        current_url = _run_git(
            ["remote", "get-url", "origin"],
            cwd=local_path,
            env=env,
            action="read git remote",
        ).strip()
        if current_url != remote_url:
            raise KeywharfError(
                f"Host repo remote URL mismatch for {local_path}: origin={current_url}, configured={remote_url}"
            )
        _run_git(
            ["pull", "--ff-only", "origin"],
            cwd=local_path,
            env=env,
            action="sync host repo",
        )
        return

    local_path.parent.mkdir(parents=True, exist_ok=True)
    _run_git(["clone", remote_url, str(local_path)], env=env, action="clone host repo")


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
