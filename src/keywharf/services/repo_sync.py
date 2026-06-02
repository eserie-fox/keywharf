"""Clone or sync the configured host repo."""

from __future__ import annotations

from keywharf.config.resolver import ResolvedManagerConfig
from keywharf.services.host_repo_setup import (
    ensure_host_repo_path_is_ready_for_sync,
    ensure_host_repo_remote_url_is_configured,
)
from keywharf.services.privilege import can_write_directory, root_owned_hint
from keywharf.storage.git_repo import clone_or_sync_repository


def sync_host_repo(config: ResolvedManagerConfig) -> None:
    host_repo_remote_url = ensure_host_repo_remote_url_is_configured(config)
    ensure_host_repo_path_is_ready_for_sync(config)
    clone_or_sync_repository(host_repo_remote_url, config.host_repo_path)


def analyze_host_repo_sync_root_requirements(
    config: ResolvedManagerConfig,
) -> list[str]:
    """Return concrete privilege reasons for host-repo mutation."""

    ensure_host_repo_remote_url_is_configured(config)
    ensure_host_repo_path_is_ready_for_sync(config)

    if config.host_repo_path.exists():
        if can_write_directory(config.host_repo_path):
            return []
        hint = root_owned_hint(config.host_repo_path)
        return [f"host repo path is not writable by current user: {config.host_repo_path}{hint}"]

    if can_write_directory(config.host_repo_path.parent):
        return []
    hint = root_owned_hint(config.host_repo_path.parent)
    return [
        f"host repo parent is not writable by current user: {config.host_repo_path.parent}{hint}"
    ]
