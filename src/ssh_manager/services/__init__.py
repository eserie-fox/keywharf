"""Service layer exports."""

from ssh_manager.services.apply import apply_selected_state
from ssh_manager.services.apply_managed_config import apply_managed_config, validate_managed_config
from ssh_manager.services.check import validate_remote_repo_config
from ssh_manager.services.init import initialize_workspace, resolve_init_paths
from ssh_manager.services.install_include import detect_include, install_managed_include
from ssh_manager.services.local_hosts import load_local_hosts, render_local_hosts, write_local_hosts
from ssh_manager.services.local_view import get_local_status, list_local_statuses
from ssh_manager.services.pull import pull_remote_repo
from ssh_manager.services.render import render_selected_state
from ssh_manager.services.render_managed_config import render_managed_config
from ssh_manager.services.remote_hosts import (
    build_remote_host_config_from_selection,
    build_remote_host_config,
    load_remote_host_list,
    load_remote_host_map,
    resolve_selection,
    remote_config_path,
    remote_host_map_to_dict,
    validate_remote_host_definitions,
)
from ssh_manager.services.selections import deselect_host, load_selected_state, select_host
from ssh_manager.services.validate import validate_workspace

__all__ = [
    "apply_selected_state",
    "apply_managed_config",
    "build_remote_host_config_from_selection",
    "build_remote_host_config",
    "deselect_host",
    "detect_include",
    "get_local_status",
    "initialize_workspace",
    "load_local_hosts",
    "load_selected_state",
    "list_local_statuses",
    "load_remote_host_list",
    "load_remote_host_map",
    "install_managed_include",
    "pull_remote_repo",
    "render_selected_state",
    "render_managed_config",
    "resolve_init_paths",
    "resolve_selection",
    "remote_config_path",
    "remote_host_map_to_dict",
    "render_local_hosts",
    "select_host",
    "validate_remote_host_definitions",
    "validate_remote_repo_config",
    "validate_managed_config",
    "validate_workspace",
    "write_local_hosts",
]
