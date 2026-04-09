"""Install or detect an OpenSSH Include for the manager-owned config."""

from __future__ import annotations

from ssh_manager.domain.models import ManagerConfig
from ssh_manager.domain.results import IncludeInstallResult
from ssh_manager.storage.managed_state import include_is_installed, install_include


def detect_include(config: ManagerConfig) -> bool:
    return include_is_installed(config)


def install_managed_include(
    config: ManagerConfig,
    *,
    dry_run: bool = False,
    backup: bool = True,
) -> IncludeInstallResult:
    return install_include(config, dry_run=dry_run, backup=backup)
