from __future__ import annotations

from pathlib import Path

from ssh_manager.runtime.config import load_manager_config
from ssh_manager.services.install_include import detect_include, install_managed_include
from ssh_manager.storage.managed_state import include_line_for_config
from tests.support import make_data_root, write_local_ssh_config, write_manager_config


def test_detect_include_exact_match(tmp_path: Path) -> None:
    data_root = make_data_root(tmp_path)
    config_path = data_root / "config.json"
    write_manager_config(config_path)
    config = load_manager_config(config_path, data_root=data_root)
    write_local_ssh_config(config.ssh_dir, f"{include_line_for_config(config)}\n")

    assert detect_include(config) is True


def test_detect_include_glob_match(tmp_path: Path) -> None:
    data_root = make_data_root(tmp_path)
    config_path = data_root / "config.json"
    write_manager_config(config_path)
    config = load_manager_config(config_path, data_root=data_root)
    include_glob = (config.managed_config_path.parent / "*.conf").as_posix()
    write_local_ssh_config(config.ssh_dir, f"Include {include_glob}\n")

    assert detect_include(config) is True


def test_install_include_appends_minimal_block_without_rewriting_existing_content(tmp_path: Path) -> None:
    data_root = make_data_root(tmp_path)
    config_path = data_root / "config.json"
    write_manager_config(config_path)
    config = load_manager_config(config_path, data_root=data_root)
    original = "Host custom\n  HostName custom.example.com\n"
    main_config_path = write_local_ssh_config(config.ssh_dir, original)

    result = install_managed_include(config)

    final_content = main_config_path.read_text(encoding="utf-8")
    assert result.already_present is False
    assert result.changed is True
    assert final_content.startswith(original)
    assert "# Added by ssh-manager" in final_content
    assert result.include_line in final_content


def test_install_include_dry_run_does_not_write_main_config(tmp_path: Path) -> None:
    data_root = make_data_root(tmp_path)
    config_path = data_root / "config.json"
    write_manager_config(config_path)
    config = load_manager_config(config_path, data_root=data_root)

    result = install_managed_include(config, dry_run=True)

    assert result.already_present is False
    assert result.changed is True
    assert result.dry_run is True
    assert not config.main_config_path.exists()
    assert result.include_line in result.rendered_content
