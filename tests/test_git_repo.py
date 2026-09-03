from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from git import Actor, Repo
from git.exc import GitCommandError
from git.remote import Remote

import keywharf.storage.git_repo as git_repo_service
from keywharf.domain.errors import KeywharfError
from keywharf.storage.git_repo import clone_or_sync_repository

GIT_ACTOR = Actor("Keywharf Tests", "tests@example.com")


def test_system_git_preflight_and_noninteractive_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(git_repo_service.shutil, "which", lambda command: None)
    with pytest.raises(KeywharfError, match="git is not available"):
        clone_or_sync_repository("file:///remote.git", tmp_path / "clone")

    environment = git_repo_service._build_git_environment("git@example.com:org/hosts.git")
    assert environment["GIT_TERMINAL_PROMPT"] == "0"
    assert environment["GIT_ASKPASS"] == "echo"
    assert "BatchMode=yes" in environment["GIT_SSH_COMMAND"]
    assert "StrictHostKeyChecking=accept-new" in environment["GIT_SSH_COMMAND"]


@pytest.mark.skipif(shutil.which("git") is None, reason="system Git is required")
def test_clone_into_absent_and_empty_directories(tmp_path: Path) -> None:
    _, remote = _create_remote(tmp_path)
    absent = tmp_path / "absent"
    empty = tmp_path / "empty"
    empty.mkdir()

    clone_or_sync_repository(str(remote), absent)
    clone_or_sync_repository(str(remote), empty)

    assert (absent / "config.json").read_text(encoding="utf-8") == "[]\n"
    assert (empty / "config.json").read_text(encoding="utf-8") == "[]\n"
    with Repo(absent, search_parent_directories=False) as repo:
        assert repo.remotes.origin.url == str(remote)


@pytest.mark.skipif(shutil.which("git") is None, reason="system Git is required")
def test_non_repository_and_local_first_paths_are_actionable(tmp_path: Path) -> None:
    _, remote = _create_remote(tmp_path)
    unrelated = tmp_path / "unrelated"
    unrelated.mkdir()
    (unrelated / "note.txt").write_text("not a repo\n", encoding="utf-8")

    with pytest.raises(KeywharfError, match="not a git repository"):
        clone_or_sync_repository(str(remote), unrelated)

    bootstrap = tmp_path / "bootstrap"
    bootstrap.mkdir()
    (bootstrap / "config.json").write_text("[]\n", encoding="utf-8")
    with pytest.raises(KeywharfError, match="local-first bootstrap"):
        clone_or_sync_repository(str(remote), bootstrap)

    nested = tmp_path / "source" / "nested"
    nested.mkdir()
    (nested / "note.txt").write_text("not the worktree root\n", encoding="utf-8")
    with pytest.raises(KeywharfError, match="not a git repository"):
        clone_or_sync_repository(str(remote), nested)


@pytest.mark.skipif(shutil.which("git") is None, reason="system Git is required")
def test_origin_match_and_fast_forward_update(tmp_path: Path) -> None:
    source, remote = _create_remote(tmp_path)
    clone = tmp_path / "clone"
    clone_or_sync_repository(str(remote), clone)

    with pytest.raises(KeywharfError) as mismatch:
        clone_or_sync_repository("https://user:password@example.com/other.git", clone)
    assert "remote URL mismatch" in str(mismatch.value)
    assert "password" not in str(mismatch.value)

    (source / "config.json").write_text('[{"ServerName":"updated"}]\n', encoding="utf-8")
    with Repo(source, search_parent_directories=False) as repo:
        _commit(repo, ["config.json"], "Update host repo")
        repo.remotes.origin.push("main")

    clone_or_sync_repository(str(remote), clone)
    assert "updated" in (clone / "config.json").read_text(encoding="utf-8")


@pytest.mark.skipif(shutil.which("git") is None, reason="system Git is required")
def test_diverged_history_is_not_merged(tmp_path: Path) -> None:
    source, remote = _create_remote(tmp_path)
    clone = tmp_path / "clone"
    clone_or_sync_repository(str(remote), clone)

    (source / "remote.txt").write_text("remote\n", encoding="utf-8")
    with Repo(source, search_parent_directories=False) as repo:
        _commit(repo, ["remote.txt"], "Remote change")
        repo.remotes.origin.push("main")

    (clone / "local.txt").write_text("local\n", encoding="utf-8")
    with Repo(clone, search_parent_directories=False) as repo:
        _commit(repo, ["local.txt"], "Local change")

    with pytest.raises(KeywharfError, match="sync host repo"):
        clone_or_sync_repository(str(remote), clone)


@pytest.mark.skipif(shutil.which("git") is None, reason="system Git is required")
def test_linked_worktree_is_supported(tmp_path: Path) -> None:
    source, remote = _create_remote(tmp_path)
    linked = tmp_path / "linked"
    with Repo(source, search_parent_directories=False) as repo:
        repo.git.worktree("add", "-b", "linked", str(linked), "origin/main")

    assert (linked / ".git").is_file()
    clone_or_sync_repository(str(remote), linked)


@pytest.mark.skipif(shutil.which("git") is None, reason="system Git is required")
def test_git_failure_is_sanitized_and_repository_is_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, remote = _create_remote(tmp_path)
    clone = tmp_path / "clone"
    clone_or_sync_repository(str(remote), clone)
    closed: list[Path] = []
    original_close = Repo.close

    def record_close(repo: Repo) -> None:
        if repo.working_tree_dir is not None:
            closed.append(Path(repo.working_tree_dir))
        original_close(repo)

    def fail_pull(self: Remote, *args: object, **kwargs: object) -> None:
        del self, args, kwargs
        raise GitCommandError(
            ["git", "pull", "https://user:password@example.com/private.git"],
            128,
            stderr="fatal: failed https://user:password@example.com/private.git",
        )

    monkeypatch.setattr(Repo, "close", record_close)
    monkeypatch.setattr(Remote, "pull", fail_pull)

    with pytest.raises(KeywharfError) as caught:
        clone_or_sync_repository(str(remote), clone)

    message = str(caught.value)
    assert "sync host repo" in message
    assert "password" not in message
    assert "git pull" not in message
    assert clone in closed


def _commit(repo: Repo, paths: list[str], message: str) -> None:
    repo.index.add(paths)
    repo.index.commit(message, author=GIT_ACTOR, committer=GIT_ACTOR)


def _create_remote(tmp_path: Path) -> tuple[Path, Path]:
    source = tmp_path / "source"
    source.mkdir()
    (source / "config.json").write_text("[]\n", encoding="utf-8")
    (source / ".gitignore").write_text("*.bak\n", encoding="utf-8")
    with Repo.init(source, initial_branch="main") as repo:
        _commit(repo, ["config.json", ".gitignore"], "Initialize host repo")

    remote = tmp_path / "remote.git"
    with Repo.init(remote, bare=True, initial_branch="main"):
        pass
    with Repo(source, search_parent_directories=False) as repo:
        origin = repo.create_remote("origin", str(remote))
        origin.push("main:main", set_upstream=True)
    return source, remote
