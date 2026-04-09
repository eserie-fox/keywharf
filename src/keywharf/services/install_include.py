"""Install or detect an OpenSSH Include for the manager-owned config."""

from __future__ import annotations

from keywharf.config.resolver import ResolvedManagerConfig
from keywharf.domain.results import IncludeInstallResult
from keywharf.services.privilege import can_read_path, can_write_file, root_owned_hint
from keywharf.storage.managed_files import include_is_installed, install_include


def detect_include(config: ResolvedManagerConfig) -> bool:
    return include_is_installed(config)


def install_managed_include(
    config: ResolvedManagerConfig,
    *,
    dry_run: bool = False,
    backup: bool = True,
) -> IncludeInstallResult:
    return install_include(config, dry_run=dry_run, backup=backup)


def analyze_install_include_root_requirements(
    config: ResolvedManagerConfig,
) -> list[str]:
    """Return concrete privilege reasons for main-config include installation."""

    reasons: list[str] = []
    if config.main_config_path.exists() and not can_read_path(config.main_config_path):
        reasons.append(
            f"main SSH config is not readable by current user: {config.main_config_path}{root_owned_hint(config.main_config_path)}"
        )
    if not can_write_file(config.main_config_path):
        reasons.append(
            f"main SSH config path is not writable by current user: {config.main_config_path}{root_owned_hint(config.main_config_path.parent)}"
        )
    return reasons
