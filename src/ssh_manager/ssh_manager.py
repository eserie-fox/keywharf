"""Backward-compatible facade over the refactored services."""

from __future__ import annotations

from ssh_manager.domain.models import RemoteHostDefinition, SSHHostConfig
from ssh_manager.runtime.config import Config
from ssh_manager.services.check import validate_remote_repo_config
from ssh_manager.services.local_hosts import load_local_hosts, render_local_hosts, write_local_hosts
from ssh_manager.services.operations import preview_add_host
from ssh_manager.services.pull import pull_remote_repo
from ssh_manager.services.remote_hosts import load_remote_host_map, remote_host_map_to_dict
from ssh_manager.storage.ssh_files import (
    copy_identity_file,
    delete_identity_file,
    list_managed_key_files,
)


class SSHManager:
    """Legacy facade kept for compatibility while services own the implementation."""

    def __init__(self, config_path: str | None = None):
        self.config = Config(config_path)
        self._model = self.config.model
        self._remote_hosts: dict[str, RemoteHostDefinition] = {}
        self.ssh_key_repo_config: dict[str, dict[str, object]] = {}

    def get_ssh_directory(self) -> str:
        return self._model.ssh_dir.as_posix()

    def get_abs_path_based_on_ssh_key_repo_config(self, relevant_path: str) -> str:
        return self._model.resolve_from_local_repo(relevant_path).as_posix()

    def get_ssh_config_path(self) -> str:
        return self._model.ssh_config_path().as_posix()

    def get_ssh_key_list(self) -> list[str]:
        return list_managed_key_files(self._model.managed_keys_dir)

    def pull_ssh_key_repo(self) -> None:
        pull_remote_repo(self._model)

    def check_ssh_key_repo_config(self) -> bool:
        return validate_remote_repo_config(self._model).ok

    def read_ssh_key_repo_config(self) -> None:
        self._remote_hosts = load_remote_host_map(self._model)
        self.ssh_key_repo_config = remote_host_map_to_dict(self._remote_hosts)

    def parse_current_ssh_config(self) -> list[SSHHostConfig]:
        return load_local_hosts(self._model)

    def get_ssh_key_repo_server_names(self) -> list[str]:
        return list(self.ssh_key_repo_config.keys())

    def generate_ssh_config(
        self, server_name: str, endpoint_id: int = 0, auth_id: int = 0
    ) -> SSHHostConfig:
        if not self._remote_hosts:
            self.read_ssh_key_repo_config()
        return preview_add_host(
            self._model,
            self._remote_hosts,
            server_name=server_name,
            endpoint_id=endpoint_id,
            auth_id=auth_id,
        )

    def delete_identify_file(self, ssh_host_config: SSHHostConfig) -> None:
        delete_identity_file(ssh_host_config.get_ssh_identity_file())

    def render_ssh_config(self, configs: list[SSHHostConfig]) -> str:
        return render_local_hosts(configs)

    def write_ssh_config(self, configs: list[SSHHostConfig], backup: bool = True) -> None:
        write_local_hosts(self._model, configs, backup=backup)

    def copy_identify_file(self, ssh_host_config: SSHHostConfig) -> None:
        copy_identity_file(
            ssh_host_config.get_ssh_original_identity_file(),
            ssh_host_config.get_ssh_identity_file(),
        )

    def append_ssh_host_config(self, ssh_host_config: SSHHostConfig) -> None:
        existing = load_local_hosts(self._model)
        write_local_hosts(self._model, [*existing, ssh_host_config], backup=False)
