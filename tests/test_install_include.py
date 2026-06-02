from __future__ import annotations

from pathlib import Path

from keywharf.services.install_include import detect_include, install_managed_include
from keywharf.storage.managed_files import include_line_for_config
from tests.support import (
    load_config,
    make_workspace,
    write_local_ssh_config,
    write_manager_config,
)


def test_install_include_detects_exact_include_line(tmp_path: Path) -> None:
    workspace_root = make_workspace(tmp_path)
    config_path = write_manager_config(workspace_root / "config.json")
    config = load_config(config_path, workspace_root=workspace_root)
    write_local_ssh_config(config.ssh_dir, include_line_for_config(config) + "\n")

    assert detect_include(config) is True


def test_install_include_detects_glob_include(tmp_path: Path) -> None:
    workspace_root = make_workspace(tmp_path)
    config_path = write_manager_config(workspace_root / "config.json")
    config = load_config(config_path, workspace_root=workspace_root)
    write_local_ssh_config(
        config.ssh_dir,
        f"Include {config.managed_config_path.parent.as_posix()}/*.conf\n",
    )

    assert detect_include(config) is True


def test_install_include_appends_minimal_block_without_rewriting_existing_content(
    tmp_path: Path,
) -> None:
    workspace_root = make_workspace(tmp_path)
    config_path = write_manager_config(workspace_root / "config.json")
    config = load_config(config_path, workspace_root=workspace_root)
    write_local_ssh_config(config.ssh_dir, "Host untouched\n  HostName untouched.example.com\n")

    result = install_managed_include(config)

    content = config.main_config_path.read_text(encoding="utf-8")
    assert result.changed is True
    assert "Host untouched" in content
    assert include_line_for_config(config) in content


def test_install_include_dry_run_does_not_write(tmp_path: Path) -> None:
    workspace_root = make_workspace(tmp_path)
    config_path = write_manager_config(workspace_root / "config.json")
    config = load_config(config_path, workspace_root=workspace_root)
    write_local_ssh_config(config.ssh_dir, "Host untouched\n  HostName untouched.example.com\n")
    before = config.main_config_path.read_text(encoding="utf-8")

    result = install_managed_include(config, dry_run=True)

    assert result.changed is True
    assert config.main_config_path.read_text(encoding="utf-8") == before
