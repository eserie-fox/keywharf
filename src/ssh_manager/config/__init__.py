"""Formal manager-config helpers."""

from ssh_manager.config.loader import (
    DEFAULT_CONFIG_FILE_NAME,
    MANAGER_DEFAULTS_RESOURCE_SPEC,
    load_resolved_manager_config,
    load_manager_defaults,
    merge_manager_config_mapping,
    resolve_config_path,
)
from ssh_manager.config.merge import config_deep_merge
from ssh_manager.config.models import ManagerConfig
from ssh_manager.config.resolver import ResolvedManagerConfig, resolve_manager_config

__all__ = [
    "DEFAULT_CONFIG_FILE_NAME",
    "MANAGER_DEFAULTS_RESOURCE_SPEC",
    "ManagerConfig",
    "ResolvedManagerConfig",
    "config_deep_merge",
    "load_resolved_manager_config",
    "load_manager_defaults",
    "merge_manager_config_mapping",
    "resolve_config_path",
    "resolve_manager_config",
]
