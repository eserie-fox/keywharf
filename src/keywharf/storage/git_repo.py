from __future__ import annotations

import os
import re
import shutil
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path, PureWindowsPath
from typing import TYPE_CHECKING

from keywharf.domain.errors import KeywharfError
from keywharf.storage.host_repo import HOST_REPO_CONFIG_FILENAME

if TYPE_CHECKING:
    from git import Repo
    from git.exc import GitCommandError
    from git.remote import Remote

_URL_USERINFO_RE = re.compile(r"(?P<scheme>[a-zA-Z][a-zA-Z0-9+.-]*://)[^/@\s]+@")


def _build_git_environment(remote_url: str) -> dict[str, str]:
    environment = {
        **os.environ,
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_ASKPASS": "echo",
    }
    if remote_url.startswith("git@") or remote_url.startswith("ssh://"):
        environment["GIT_SSH_COMMAND"] = "ssh -o StrictHostKeyChecking=accept-new -o BatchMode=yes"
    return environment


def clone_or_sync_repository(remote_url: str, local_path: Path) -> None:
    _require_git()
    if local_path.exists():
        if not local_path.is_dir():
            raise KeywharfError(f"Host repo path exists but is not a directory: {local_path}")
        if _directory_is_empty(local_path):
            _clone_repository(remote_url, local_path)
            return
        with _open_exact_repository(local_path) as repo:
            origin = _require_origin(repo, local_path)
            current_url = _origin_url(origin, local_path)
            if not _remote_urls_match(current_url, remote_url):
                raise KeywharfError(
                    f"Host repo remote URL mismatch for {local_path}: "
                    f"origin={_redact_url_userinfo(current_url)}, "
                    f"configured={_redact_url_userinfo(remote_url)}"
                )
            with _translate_git_failures(f"sync host repo at {local_path}"):
                with repo.git.custom_environment(**_build_git_environment(remote_url)):
                    origin.pull(
                        ff_only=True,
                        allow_unsafe_protocols=False,
                        allow_unsafe_options=False,
                    )
        return

    try:
        local_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise KeywharfError(
            f"Could not create host repo parent {local_path.parent}: {exc}"
        ) from exc
    _clone_repository(remote_url, local_path)


def _clone_repository(remote_url: str, local_path: Path) -> None:
    with _translate_git_failures(f"clone host repo into {local_path}"):
        from git import Repo

        repo = Repo.clone_from(
            remote_url,
            local_path,
            env=_build_git_environment(remote_url),
            allow_unsafe_protocols=False,
            allow_unsafe_options=False,
        )
        try:
            _verify_worktree_root(repo, local_path)
            origin = _require_origin(repo, local_path)
            if not _remote_urls_match(_origin_url(origin, local_path), remote_url):
                raise KeywharfError(
                    f"Cloned host repo origin does not match configured remote: {local_path}"
                )
        finally:
            repo.close()


@contextmanager
def _open_exact_repository(local_path: Path) -> Iterator[Repo]:
    from git.exc import InvalidGitRepositoryError, NoSuchPathError

    with _translate_git_failures(f"open host repo at {local_path}"):
        from git import Repo

        try:
            repo = Repo(local_path, search_parent_directories=False)
        except (InvalidGitRepositoryError, NoSuchPathError) as exc:
            raise _not_repository_error(local_path) from exc
    try:
        with _translate_git_failures(f"inspect host repo at {local_path}"):
            _verify_worktree_root(repo, local_path)
    except KeywharfError:
        with _translate_git_failures(f"close host repo at {local_path}"):
            repo.close()
        raise

    try:
        yield repo
    finally:
        with _translate_git_failures(f"close host repo at {local_path}"):
            repo.close()


def _verify_worktree_root(repo: Repo, local_path: Path) -> None:
    if repo.bare or repo.working_tree_dir is None:
        raise _not_repository_error(local_path)
    actual = Path(repo.working_tree_dir).resolve(strict=False)
    expected = local_path.resolve(strict=False)
    if actual != expected:
        raise KeywharfError(
            f"Git worktree root {actual} does not match configured host repo path {expected}"
        )


def _require_origin(repo: Repo, local_path: Path) -> Remote:
    for remote in repo.remotes:
        if remote.name == "origin":
            return remote
    raise KeywharfError(f"Host repo has no origin remote: {local_path}")


def _origin_url(origin: Remote, local_path: Path) -> str:
    with _translate_git_failures(f"read host repo origin at {local_path}"):
        return origin.url


def _remote_urls_match(actual: str, configured: str) -> bool:
    actual_windows_path = PureWindowsPath(actual)
    configured_windows_path = PureWindowsPath(configured)
    if actual_windows_path.is_absolute() and configured_windows_path.is_absolute():
        return actual_windows_path == configured_windows_path
    return actual == configured


def _not_repository_error(local_path: Path) -> KeywharfError:
    bootstrap_hint = ""
    if (local_path / HOST_REPO_CONFIG_FILENAME).exists():
        bootstrap_hint = (
            " This looks like a local-first bootstrap created by "
            "'keywharf repo init'. Initialize git and add a remote yourself, "
            "or remove this directory before running 'keywharf repo sync'."
        )
    return KeywharfError(
        f"Host repo path exists but is not a git repository: {local_path}.{bootstrap_hint}"
    )


def _directory_is_empty(path: Path) -> bool:
    try:
        next(path.iterdir())
    except StopIteration:
        return True
    except OSError as exc:
        raise KeywharfError(f"Could not inspect host repo directory {path}: {exc}") from exc
    return False


def _require_git() -> None:
    if shutil.which("git") is None:
        raise KeywharfError("git is not available in PATH.")


@contextmanager
def _translate_git_failures(action: str) -> Iterator[None]:
    from git.exc import (
        GitCommandError,
        GitCommandNotFound,
        InvalidGitRepositoryError,
        NoSuchPathError,
    )

    try:
        yield
    except GitCommandNotFound as exc:
        raise KeywharfError("git is not available in PATH.") from exc
    except GitCommandError as exc:
        raise KeywharfError(f"Failed to {action}: {_git_command_message(exc)}") from exc
    except (InvalidGitRepositoryError, NoSuchPathError) as exc:
        raise KeywharfError(f"Failed to {action}: invalid Git repository or path") from exc
    except OSError as exc:
        raise KeywharfError(f"Failed to {action}: {exc}") from exc


def _git_command_message(exc: GitCommandError) -> str:
    message = _git_output(exc.stderr) or _git_output(exc.stdout) or "unknown Git error"
    return _redact_url_userinfo(message)


def _git_output(value: str | bytes | None) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace").strip()
    return value.strip() if value else ""


def _redact_url_userinfo(message: str) -> str:
    return _URL_USERINFO_RE.sub(lambda match: f"{match.group('scheme')}<redacted>@", message)
