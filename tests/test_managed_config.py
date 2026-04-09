from __future__ import annotations

from pathlib import Path

import pytest

from ssh_manager.domain.errors import SSHManagerError
from ssh_manager.runtime.config import load_manager_config
from ssh_manager.services.apply_managed_config import apply_managed_config
from ssh_manager.services.remote_hosts import build_remote_host_config, load_remote_host_map
from ssh_manager.services.render_managed_config import render_managed_config
from tests.support import (
    make_data_root,
    write_identity_file,
    write_local_ssh_config,
    write_manager_config,
    write_managed_ssh_config,
    write_remote_repo_config,
)


def test_render_managed_config_uses_managed_keys_dir(tmp_path: Path) -> None:
    data_root = make_data_root(tmp_path)
    config_path = data_root / "config.json"
    write_manager_config(config_path)
    repo_root = data_root / "repos" / "keys"
    write_identity_file(repo_root)
    write_remote_repo_config(repo_root)
    config = load_manager_config(config_path, data_root=data_root)
    host = build_remote_host_config(
        config,
        load_remote_host_map(config),
        server_name="demo",
    )

    rendered = render_managed_config([host])

    assert "# This file is managed by ssh_manager" in rendered
    assert f"IdentityFile {config.managed_keys_dir / 'demo' / 'id_demo'}" in rendered
    assert "Include " not in rendered


def test_apply_managed_config_only_writes_manager_owned_file(tmp_path: Path) -> None:
    data_root = make_data_root(tmp_path)
    config_path = data_root / "config.json"
    write_manager_config(config_path)
    repo_root = data_root / "repos" / "keys"
    write_identity_file(repo_root)
    write_remote_repo_config(repo_root)
    config = load_manager_config(config_path, data_root=data_root)
    main_config = write_local_ssh_config(
        config.ssh_dir,
        "Host user-main\n  HostName user.example.com\n",
    )
    host = build_remote_host_config(
        config,
        load_remote_host_map(config),
        server_name="demo",
    )

    applied_path = apply_managed_config(config, render_managed_config([host]))

    assert applied_path == config.managed_config_path
    assert config.managed_config_path.exists()
    assert "Host demo" in config.managed_config_path.read_text(encoding="utf-8")
    assert main_config.read_text(encoding="utf-8") == "Host user-main\n  HostName user.example.com\n"


def test_apply_managed_config_preserves_existing_file_on_validation_failure(tmp_path: Path) -> None:
    data_root = make_data_root(tmp_path)
    config_path = data_root / "config.json"
    write_manager_config(config_path)
    config = load_manager_config(config_path, data_root=data_root)
    write_managed_ssh_config(
        config.managed_config_path,
        "# This file is managed by ssh_manager\n\nHost stable\n  HostName stable.example.com\n",
    )
    before = config.managed_config_path.read_text(encoding="utf-8")

    with pytest.raises(SSHManagerError):
        apply_managed_config(config, "Host broken\n  BadDirective\n")

    assert config.managed_config_path.read_text(encoding="utf-8") == before
