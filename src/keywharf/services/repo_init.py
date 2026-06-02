"""Bootstrap a local-first host repo skeleton."""

from __future__ import annotations

from pathlib import Path

from keywharf.config.resolver import ResolvedManagerConfig
from keywharf.config.resources import render_template
from keywharf.domain.errors import KeywharfError
from keywharf.domain.results import HostRepoInitResult
from keywharf.services.privilege import (
    can_write_directory,
    can_write_file,
    root_owned_hint,
)
from keywharf.storage.host_repo import host_repo_config_path
from keywharf.storage.json_store import write_json_value

HOST_REPO_GITIGNORE_TEMPLATE = "host_repo_gitignore.j2"


def initialize_host_repo(config: ResolvedManagerConfig) -> HostRepoInitResult:
    host_repo_path = config.host_repo_path
    config_path = host_repo_config_path(config)
    created_paths: list[Path] = []

    if host_repo_path.exists():
        if not host_repo_path.is_dir():
            raise KeywharfError(f"Host repo path exists but is not a directory: {host_repo_path}")
        if config_path.exists():
            raise KeywharfError(f"Host repo is already initialized at {config_path}.")
        if not (host_repo_path / ".git").is_dir() and any(host_repo_path.iterdir()):
            raise KeywharfError(
                f"Host repo path exists but is neither empty nor a git repository: {host_repo_path}"
            )
    else:
        host_repo_path.mkdir(parents=True, exist_ok=False)
        created_paths.append(host_repo_path)

    keys_dir = host_repo_path / "keys"
    if not keys_dir.exists():
        keys_dir.mkdir(parents=True, exist_ok=False)
        created_paths.append(keys_dir)

    write_json_value(config_path, [])
    created_paths.append(config_path)

    gitignore_path = host_repo_path / ".gitignore"
    if not gitignore_path.exists():
        gitignore_path.write_text(
            render_template(HOST_REPO_GITIGNORE_TEMPLATE) + "\n",
            encoding="utf-8",
        )
        created_paths.append(gitignore_path)

    return HostRepoInitResult(
        host_repo_path=host_repo_path,
        config_path=config_path,
        created_paths=created_paths,
    )


def analyze_host_repo_init_root_requirements(
    config: ResolvedManagerConfig,
) -> list[str]:
    """Return concrete privilege reasons for bootstrapping the host repo skeleton."""

    host_repo_path = config.host_repo_path
    config_path = host_repo_config_path(config)
    reasons: list[str] = []

    if host_repo_path.exists():
        if not can_write_directory(host_repo_path):
            hint = root_owned_hint(host_repo_path)
            reasons.append(
                f"host repo path is not writable by current user: {host_repo_path}{hint}"
            )
    elif not can_write_directory(host_repo_path):
        hint = root_owned_hint(host_repo_path.parent)
        reasons.append(f"host repo path is not creatable by current user: {host_repo_path}{hint}")

    for path, label in (
        (config_path, "host repo config"),
        (host_repo_path / ".gitignore", "host repo gitignore"),
        (host_repo_path / "keys", "host repo keys directory"),
    ):
        if path.exists():
            continue
        if path.name == "keys":
            if not can_write_directory(path):
                hint = root_owned_hint(path.parent)
                reasons.append(f"{label} is not creatable by current user: {path}{hint}")
            continue
        if not can_write_file(path):
            hint = root_owned_hint(path.parent)
            reasons.append(f"{label} path is not writable by current user: {path}{hint}")

    return reasons
