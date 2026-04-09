from __future__ import annotations

from pathlib import Path

from ssh_manager.runtime.config import load_manager_config, resolve_config_path
from ssh_manager.runtime.paths import (
    LEGACY_DATA_ROOT_ENV,
    LEGACY_DATA_ROOT_MARKER,
    PRIMARY_DATA_ROOT_ENV,
    PRIMARY_DATA_ROOT_MARKER,
    resolve_data_root,
)
from tests.support import make_data_root, write_manager_config


def test_resolve_config_path_prefers_cli_override(tmp_path: Path) -> None:
    data_root = make_data_root(tmp_path)
    override_path = data_root / "custom" / "manager.json"
    write_manager_config(override_path)
    write_manager_config(data_root / "config.json")

    resolved = resolve_config_path(Path("custom/manager.json"), data_root=data_root)

    assert resolved == override_path.resolve()


def test_load_manager_config_uses_absolute_config_parent_as_data_root(tmp_path: Path) -> None:
    data_root = make_data_root(tmp_path)
    config_path = data_root / "config.json"
    write_manager_config(config_path)

    loaded = load_manager_config(config_path)

    assert loaded.data_root == data_root.resolve()
    assert loaded.ssh_dir == (data_root / "ssh-home").resolve()
    assert loaded.managed_config_path == (
        data_root / "ssh-home" / "managed" / "ssh-manager.conf"
    ).resolve()
    assert loaded.state_path == (data_root / "state" / "state.json").resolve()


def test_load_manager_config_resolves_paths_from_config_dir_and_data_root(tmp_path: Path) -> None:
    data_root = make_data_root(tmp_path)
    config_path = data_root / "nested" / "configs" / "manager.json"
    write_manager_config(
        config_path,
        ssh_key_local_repo="../repos/keys",
        ssh_dir="%{DATA_ROOT}/ssh-home",
        state_path="%{DATA_ROOT}/state/custom-state.json",
    )

    loaded = load_manager_config(config_path, data_root=data_root)

    assert loaded.config_path == config_path.resolve()
    assert loaded.ssh_key_local_repo == (config_path.parent / "../repos/keys").resolve()
    assert loaded.ssh_dir == (data_root / "ssh-home").resolve()
    assert loaded.main_config_path == (data_root / "ssh-home" / "config").resolve()
    assert loaded.managed_config_path == (
        data_root / "ssh-home" / "managed" / "ssh-manager.conf"
    ).resolve()
    assert loaded.managed_keys_dir == (data_root / "ssh-home" / "managed" / "keys").resolve()
    assert loaded.state_path == (data_root / "state" / "custom-state.json").resolve()


def test_load_manager_config_allows_managed_path_overrides(tmp_path: Path) -> None:
    data_root = make_data_root(tmp_path)
    config_path = data_root / "config.json"
    write_manager_config(
        config_path,
        managed_config_path="./state/managed.conf",
        managed_keys_dir="../shared/managed-keys",
        state_path="./state/desired.json",
    )

    loaded = load_manager_config(config_path, data_root=data_root)

    assert loaded.managed_config_path == (config_path.parent / "state" / "managed.conf").resolve()
    assert loaded.managed_keys_dir == (config_path.parent / "../shared/managed-keys").resolve()
    assert loaded.state_path == (config_path.parent / "state" / "desired.json").resolve()


def test_resolve_data_root_prefers_primary_env_over_primary_marker(tmp_path: Path) -> None:
    cwd = tmp_path / "workspace"
    cwd.mkdir()
    primary_marker_root = cwd / "marker-root"
    primary_marker_root.mkdir()
    (primary_marker_root / PRIMARY_DATA_ROOT_MARKER).write_text("", encoding="utf-8")

    primary_env_root = tmp_path / "env-root"
    primary_env_root.mkdir()

    resolved = resolve_data_root(
        cwd=primary_marker_root,
        home=tmp_path / "home",
        env={PRIMARY_DATA_ROOT_ENV: str(primary_env_root)},
    )

    assert resolved == primary_env_root.resolve()


def test_resolve_data_root_prefers_primary_marker_over_legacy_aliases(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    project = workspace / "project"
    project.mkdir()
    primary_root = workspace / "primary-root"
    primary_root.mkdir()
    (primary_root / PRIMARY_DATA_ROOT_MARKER).write_text("", encoding="utf-8")

    legacy_env_root = tmp_path / "legacy-env-root"
    legacy_env_root.mkdir()
    legacy_marker_root = tmp_path / "legacy-marker-root"
    legacy_marker_root.mkdir()
    (legacy_marker_root / LEGACY_DATA_ROOT_MARKER).write_text("", encoding="utf-8")

    resolved = resolve_data_root(
        cwd=project,
        home=home,
        env={LEGACY_DATA_ROOT_ENV: str(legacy_env_root)},
    )

    assert resolved == primary_root.resolve()


def test_resolve_data_root_falls_back_to_legacy_aliases(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    legacy_root = workspace / "legacy-root"
    legacy_root.mkdir()
    (legacy_root / LEGACY_DATA_ROOT_MARKER).write_text("", encoding="utf-8")

    resolved = resolve_data_root(cwd=legacy_root, home=home, env={})

    assert resolved == legacy_root.resolve()
