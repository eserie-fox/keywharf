"""Storage layer exports."""

from ssh_manager.storage.git_repo import clone_or_pull_repository
from ssh_manager.storage.json_store import read_json_list, read_json_object, read_json_value
from ssh_manager.storage.managed_state import (
    SSH_MANAGER_INCLUDE_COMMENT,
    include_is_installed,
    include_line_for_config,
    install_include,
    managed_key_path,
    read_managed_config,
    write_managed_config,
)
from ssh_manager.storage.state_store import (
    empty_state,
    ensure_state_file,
    load_state,
    save_state,
    state_exists,
)
from ssh_manager.storage.ssh_files import (
    MANAGED_SSH_HEADER,
    copy_identity_file,
    delete_identity_file,
    list_managed_key_files,
    list_ssh_key_files,
    read_ssh_config,
    write_ssh_config,
)

__all__ = [
    "MANAGED_SSH_HEADER",
    "SSH_MANAGER_INCLUDE_COMMENT",
    "clone_or_pull_repository",
    "copy_identity_file",
    "delete_identity_file",
    "include_is_installed",
    "include_line_for_config",
    "install_include",
    "list_managed_key_files",
    "list_ssh_key_files",
    "managed_key_path",
    "empty_state",
    "ensure_state_file",
    "load_state",
    "read_managed_config",
    "read_json_list",
    "read_json_object",
    "read_json_value",
    "read_ssh_config",
    "save_state",
    "state_exists",
    "write_managed_config",
    "write_ssh_config",
]
