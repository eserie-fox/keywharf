"""Remote repository synchronization."""

from __future__ import annotations

from ssh_manager.domain.models import ManagerConfig
from ssh_manager.storage.git_repo import clone_or_pull_repository


def pull_remote_repo(config: ManagerConfig) -> None:
    clone_or_pull_repository(config.ssh_key_remote_repo, config.ssh_key_local_repo)
