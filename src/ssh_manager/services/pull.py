"""Remote repository synchronization."""

from __future__ import annotations

from ssh_manager.config.resolver import ResolvedManagerConfig
from ssh_manager.services.privilege import can_write_directory, root_owned_hint
from ssh_manager.storage.git_repo import clone_or_pull_repository


def pull_remote_repo(config: ResolvedManagerConfig) -> None:
    clone_or_pull_repository(config.ssh_key_remote_repo, config.ssh_key_local_repo)


def analyze_pull_root_requirements(config: ResolvedManagerConfig) -> list[str]:
    """Return concrete privilege reasons for local repo mutation."""

    if config.ssh_key_local_repo.exists():
        if can_write_directory(config.ssh_key_local_repo):
            return []
        return [
            f"local repo path is not writable by current user: {config.ssh_key_local_repo}{root_owned_hint(config.ssh_key_local_repo)}"
        ]

    if can_write_directory(config.ssh_key_local_repo.parent):
        return []
    return [
        f"local repo parent is not writable by current user: {config.ssh_key_local_repo.parent}{root_owned_hint(config.ssh_key_local_repo.parent)}"
    ]
