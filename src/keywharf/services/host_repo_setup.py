"""Shared host-repo setup guidance and validation helpers."""

from __future__ import annotations

from keywharf.config.resolver import ResolvedManagerConfig
from keywharf.domain.errors import KeywharfError
from keywharf.storage.host_repo import host_repo_config_path


def missing_host_repo_config_message(config: ResolvedManagerConfig) -> str:
    return (
        f"Host repo config not found at {host_repo_config_path(config)}. "
        "If you already have a host repo remote URL, set `host_repo_remote_url` in "
        f"{config.config_path} "
        f"and run 'keywharf --workspace {config.workspace_root} repo sync'. "
        "If you are starting from scratch, run "
        f"'keywharf --workspace {config.workspace_root} repo init'."
    )


def ensure_host_repo_remote_url_is_configured(config: ResolvedManagerConfig) -> str:
    remote_url = config.host_repo_remote_url
    if remote_url is not None:
        return remote_url

    raise KeywharfError(
        f"`host_repo_remote_url` is not configured in {config.config_path}. "
        f"If you already have a host repo remote URL, set it and run "
        f"'keywharf --workspace {config.workspace_root} repo sync'. "
        "If you are starting from scratch, run "
        f"'keywharf --workspace {config.workspace_root} repo init'.",
        exit_code=2,
    )


def ensure_host_repo_path_is_ready_for_sync(config: ResolvedManagerConfig) -> None:
    host_repo_path = config.host_repo_path
    if not host_repo_path.exists():
        return
    if not host_repo_path.is_dir():
        raise KeywharfError(f"Host repo path exists but is not a directory: {host_repo_path}")
    if (host_repo_path / ".git").exists():
        return
    if host_repo_config_path(config).is_file():
        raise KeywharfError(
            f"Host repo path exists but is not a git repository: {host_repo_path}. "
            "This looks like a local-first bootstrap created by 'keywharf repo init'. "
            "Initialize git and add a remote yourself, or remove this directory before running "
            "'keywharf repo sync'."
        )
