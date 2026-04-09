"""Validation service for the remote repo config."""

from __future__ import annotations

from ssh_manager.domain.models import ManagerConfig
from ssh_manager.domain.results import ValidationResult
from ssh_manager.services.remote_hosts import load_remote_host_list


def validate_remote_repo_config(config: ManagerConfig) -> ValidationResult:
    errors: list[str] = []
    remote_hosts = load_remote_host_list(config)
    if not remote_hosts:
        errors.append("Config file is empty")

    for remote_host in remote_hosts:
        if not remote_host.server_name:
            errors.append("Server name is empty")
            continue
        for auth in remote_host.authentication:
            if not auth.identity_file:
                continue
            identity_path = config.resolve_from_local_repo(auth.identity_file)
            if not identity_path.exists():
                errors.append(f"Identity file {identity_path.as_posix()} not found")

    return ValidationResult(ok=not errors, errors=errors)
