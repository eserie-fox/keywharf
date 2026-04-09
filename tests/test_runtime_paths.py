from __future__ import annotations

from pathlib import Path

from keywharf.config.loader import resolve_config_path
from keywharf.config.models import ManagerConfig
from keywharf.config.resolver import resolve_manager_config
from keywharf.runtime.paths import (
    DATA_ROOT_ENV,
    DATA_ROOT_MARKER,
    default_home_workspace,
    resolve_data_root,
)
from tests.support import load_config, make_data_root, write_manager_config


def test_resolve_config_path_prefers_cli_override(tmp_path: Path) -> None:
    data_root = make_data_root(tmp_path)
    override_path = data_root / "custom" / "manager.json"
    write_manager_config(override_path)
    write_manager_config(data_root / "config.json")

    resolved = resolve_config_path(Path("custom/manager.json"), data_root=data_root)

    assert resolved == override_path.resolve()


def test_load_resolved_manager_config_uses_absolute_config_parent_as_data_root(tmp_path: Path) -> None:
    data_root = make_data_root(tmp_path)
    config_path = data_root / "config.json"
    write_manager_config(config_path)

    loaded = load_config(config_path)

    assert loaded.data_root == data_root.resolve()
    assert loaded.ssh_dir == (data_root / "ssh-home").resolve()
    assert loaded.managed_config_path == (data_root / "ssh-home" / "managed" / "keywharf.conf").resolve()
    assert loaded.state_path == (data_root / "state" / "state.json").resolve()


def test_runtime_resolution_is_separate_from_raw_config(tmp_path: Path) -> None:
    raw = ManagerConfig.from_mapping(
        {
            "ssh_dir": "~/ssh-home",
            "managed_config_path": "managed/custom.conf",
            "managed_keys_dir": "managed/keys",
        }
    )
    config_path = tmp_path / "workspace" / "config.json"
    resolved = resolve_manager_config(raw, config_path=config_path, data_root=tmp_path / "workspace")

    assert raw.ssh_dir == "~/ssh-home"
    assert raw.managed_config_path == "managed/custom.conf"
    assert resolved.managed_config_path.is_absolute()
    assert resolved.managed_keys_dir.is_absolute()


def test_resolve_data_root_prefers_env_over_marker(tmp_path: Path) -> None:
    cwd = tmp_path / "workspace"
    cwd.mkdir()
    marker_root = cwd / "marker-root"
    marker_root.mkdir()
    (marker_root / DATA_ROOT_MARKER).write_text("", encoding="utf-8")
    write_manager_config(marker_root / "config.json")

    env_root = tmp_path / "env-root"
    env_root.mkdir()

    resolved = resolve_data_root(
        cwd=marker_root,
        home=tmp_path / "home",
        env={DATA_ROOT_ENV: str(env_root)},
    )

    assert resolved == env_root.resolve()


def test_resolve_data_root_uses_current_directory_when_workspace_is_complete(tmp_path: Path) -> None:
    workspace = make_data_root(tmp_path)
    write_manager_config(workspace / "config.json")

    resolved = resolve_data_root(cwd=workspace, home=tmp_path / "home", env={})

    assert resolved == workspace.resolve()


def test_resolve_data_root_falls_back_to_workspace_ancestor(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    workspace = make_data_root(tmp_path)
    write_manager_config(workspace / "config.json")
    nested = workspace / "nested" / "child"
    nested.mkdir(parents=True)

    resolved = resolve_data_root(cwd=nested, home=home, env={})

    assert resolved == workspace.resolve()


def test_resolve_data_root_falls_back_to_home_default_workspace(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    home_workspace = default_home_workspace(home)
    home_workspace.mkdir(parents=True)
    (home_workspace / DATA_ROOT_MARKER).write_text("", encoding="utf-8")
    write_manager_config(home_workspace / "config.json")

    resolved = resolve_data_root(cwd=tmp_path / "other", home=home, env={})

    assert resolved == home_workspace.resolve()


def test_resolve_data_root_error_lists_checked_candidates(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    cwd = tmp_path / "cwd"
    cwd.mkdir()

    try:
        resolve_data_root(cwd=cwd, home=home, env={})
    except RuntimeError as exc:
        message = str(exc)
    else:
        raise AssertionError("resolve_data_root should have failed")

    assert "Unable to locate keywharf data root." in message
    assert str(cwd.resolve()) in message
    assert str(default_home_workspace(home)) in message
