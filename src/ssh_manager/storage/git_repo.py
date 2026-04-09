"""Git repository storage helpers."""

from __future__ import annotations

import shutil
from pathlib import Path

import git

from ssh_manager.domain.errors import SSHManagerError


def _build_git_environment(remote_repo: str) -> dict[str, str]:
    env = {
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_ASKPASS": "echo",
    }
    if remote_repo.startswith("git@") or remote_repo.startswith("ssh://"):
        env["GIT_SSH_COMMAND"] = "ssh -o StrictHostKeyChecking=accept-new -o BatchMode=yes"
    return env


def clone_or_pull_repository(remote_repo: str, local_repo: Path) -> None:
    env = _build_git_environment(remote_repo)

    try:
        if local_repo.exists():
            try:
                repo = git.Repo(local_repo)
            except git.exc.InvalidGitRepositoryError as exc:
                if local_repo.is_dir() and not any(local_repo.iterdir()):
                    shutil.rmtree(local_repo)
                    repo = git.Repo.clone_from(remote_repo, local_repo, env=env)
                else:
                    raise SSHManagerError(
                        f"Local repo path exists but is not a git repository: {local_repo}"
                    ) from exc
        else:
            local_repo.parent.mkdir(parents=True, exist_ok=True)
            repo = git.Repo.clone_from(remote_repo, local_repo, env=env)

        repo.git.update_environment(**env)

        if not repo.remotes:
            raise SSHManagerError(f"No remotes configured for local repo: {local_repo}")

        origin = repo.remotes.origin
        current_url = origin.url
        if current_url != remote_repo:
            raise SSHManagerError(
                f"Mismatch repo url, local path {local_repo} url={current_url}, remote url={remote_repo}"
            )

        origin.pull()
    except git.exc.GitError as exc:
        raise SSHManagerError(f"Failed to sync remote repo: {exc}") from exc
