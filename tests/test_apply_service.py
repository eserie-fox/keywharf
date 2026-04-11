from __future__ import annotations

from pathlib import Path

import pytest

from keywharf.domain.errors import KeywharfError
from keywharf.services.apply import apply_selected_state
from tests.support import (
    host_repo_payload,
    load_config,
    make_workspace,
    selection_payload,
    state_payload,
    write_identity_file,
    write_local_ssh_config,
    write_managed_ssh_config,
    write_manager_config,
    write_host_repo_config,
    write_state_file,
)


def test_apply_writes_only_manager_owned_files_and_cleans_stale_keys(tmp_path: Path) -> None:
    workspace_root = make_workspace(tmp_path)
    config_path = write_manager_config(workspace_root / "config.json")
    config = load_config(config_path, workspace_root=workspace_root)
    write_local_ssh_config(config.ssh_dir, "Host untouched\n  HostName untouched.example.com\n")
    host_repo_path = config.host_repo_path
    write_identity_file(host_repo_path)
    write_host_repo_config(host_repo_path, payload=host_repo_payload(endpoint_name="public", auth_name="home"))
    write_state_file(
        config.state_path,
        payload=state_payload(
            selected_hosts=[
                selection_payload(server_name="demo", endpoint_name="public", authentication_name="home")
            ]
        ),
    )
    stale_key = config.managed_keys_dir / "old" / "id_old"
    stale_key.parent.mkdir(parents=True, exist_ok=True)
    stale_key.write_text("OLD", encoding="utf-8")

    result = apply_selected_state(config)

    assert result.changed is True
    assert config.main_config_path.read_text(encoding="utf-8") == (
        "Host untouched\n  HostName untouched.example.com\n"
    )
    assert "Host demo" in config.managed_config_path.read_text(encoding="utf-8")
    assert (config.managed_keys_dir / "demo" / "id_demo").exists()
    assert not stale_key.exists()


def test_apply_preserves_existing_managed_config_when_key_copy_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    workspace_root = make_workspace(tmp_path)
    config_path = write_manager_config(workspace_root / "config.json")
    config = load_config(config_path, workspace_root=workspace_root)
    host_repo_path = config.host_repo_path
    write_identity_file(host_repo_path)
    write_host_repo_config(host_repo_path, payload=host_repo_payload(endpoint_name="public", auth_name="home"))
    write_state_file(
        config.state_path,
        payload=state_payload(
            selected_hosts=[
                selection_payload(server_name="demo", endpoint_name="public", authentication_name="home")
            ]
        ),
    )
    write_managed_ssh_config(
        config.managed_config_path,
        "# This file is managed by keywharf\n\nHost stable\n  HostName stable.example.com\n",
    )
    before = config.managed_config_path.read_text(encoding="utf-8")

    def fail_copy(*args, **kwargs):
        raise OSError("copy failed")

    monkeypatch.setattr("keywharf.services.apply.copy_identity_file", fail_copy)

    with pytest.raises(OSError):
        apply_selected_state(config)

    assert config.managed_config_path.read_text(encoding="utf-8") == before


def test_apply_rejects_empty_state_when_managed_output_exists(tmp_path: Path) -> None:
    workspace_root = make_workspace(tmp_path)
    config_path = write_manager_config(workspace_root / "config.json")
    config = load_config(config_path, workspace_root=workspace_root)
    host_repo_path = config.host_repo_path
    write_identity_file(host_repo_path)
    write_host_repo_config(host_repo_path)
    write_state_file(config.state_path, payload=state_payload())
    write_managed_ssh_config(
        config.managed_config_path,
        "# This file is managed by keywharf\n\nHost stale\n  HostName stale.example.com\n",
    )

    with pytest.raises(KeywharfError):
        apply_selected_state(config)


def test_apply_allow_empty_can_clear_non_empty_managed_output(tmp_path: Path) -> None:
    workspace_root = make_workspace(tmp_path)
    config_path = write_manager_config(workspace_root / "config.json")
    config = load_config(config_path, workspace_root=workspace_root)
    host_repo_path = config.host_repo_path
    write_identity_file(host_repo_path)
    write_host_repo_config(host_repo_path)
    write_state_file(config.state_path, payload=state_payload())
    write_managed_ssh_config(
        config.managed_config_path,
        "# This file is managed by keywharf\n\nHost stale\n  HostName stale.example.com\n",
    )

    result = apply_selected_state(config, allow_empty=True)

    assert result.changed is True
    assert "Host stale" not in config.managed_config_path.read_text(encoding="utf-8")
