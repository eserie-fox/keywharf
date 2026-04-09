"""Compatibility wrapper for remote-repository validation."""

from __future__ import annotations

from ssh_manager.domain.models import ManagerConfig
from ssh_manager.domain.results import ValidationResult
from ssh_manager.services.remote_hosts import (
    load_remote_host_list,
    validate_remote_host_definitions,
)


def validate_remote_repo_config(config: ManagerConfig) -> ValidationResult:
    return validate_remote_host_definitions(config, load_remote_host_list(config))
