from __future__ import annotations

from pathlib import Path

from keywharf.config.loader import resolve_config_path
from keywharf.config.models import ManagerConfig
from keywharf.config.resolver import resolve_manager_config
from keywharf.runtime.paths import (
    WORKSPACE_ENV,
    WORKSPACE_MARKER,
    expand_workspace_root,
    resolve_workspace_root,
)
from tests.support import load_config, make_workspace, write_manager_config


def test_resolve_config_path_prefers_cli_override(tmp_path: Path) -> None:
    workspace_root = make_workspace(tmp_path)
    override_path = workspace_root / "custom" / "manager.json"
    write_manager_config(override_path)
    write_manager_config(workspace_root / "config.json")

    resolved = resolve_config_path(Path("custom/manager.json"), workspace_root=workspace_root)

    assert resolved == override_path.resolve()


def test_load_resolved_manager_config_uses_absolute_config_parent_as_workspace_root(
    tmp_path: Path,
) -> None:
    workspace_root = make_workspace(tmp_path)
    config_path = workspace_root / "config.json"
    write_manager_config(config_path)

    loaded = load_config(config_path)

    assert loaded.workspace_root == workspace_root.resolve()
    assert loaded.ssh_dir == (workspace_root / "ssh-home").resolve()
    assert (
        loaded.managed_config_path
        == (workspace_root / "ssh-home" / "managed" / "keywharf.conf").resolve()
    )
    assert loaded.state_path == (workspace_root / "state" / "state.json").resolve()


def test_runtime_resolution_is_separate_from_raw_config(tmp_path: Path) -> None:
    raw = ManagerConfig.from_mapping(
        {
            "ssh_dir": "~/ssh-home",
            "managed_config_path": "managed/custom.conf",
            "managed_keys_dir": "managed/keys",
        }
    )
    config_path = tmp_path / "workspace" / "config.json"
    resolved = resolve_manager_config(
        raw, config_path=config_path, workspace_root=tmp_path / "workspace"
    )

    assert raw.ssh_dir == "~/ssh-home"
    assert raw.managed_config_path == "managed/custom.conf"
    assert resolved.managed_config_path.is_absolute()
    assert resolved.managed_keys_dir.is_absolute()


def test_resolve_workspace_root_prefers_env_over_auto_search(tmp_path: Path) -> None:
    cwd = tmp_path / "workspace"
    cwd.mkdir()
    marker_root = cwd / "marker-root"
    marker_root.mkdir()
    (marker_root / WORKSPACE_MARKER).write_text("", encoding="utf-8")

    env_root = tmp_path / "env-root"
    env_root.mkdir()

    resolved = resolve_workspace_root(
        cwd=marker_root,
        home=tmp_path / "home",
        env={WORKSPACE_ENV: str(env_root)},
    )

    assert resolved == env_root.resolve()


def test_expand_workspace_root_replaces_workspace_token_in_strings_and_paths(
    tmp_path: Path,
) -> None:
    workspace_root = (tmp_path / "workspace").resolve()

    assert expand_workspace_root("%{WORKSPACE}/repo", workspace_root) == str(
        workspace_root / "repo"
    )
    assert expand_workspace_root(Path("%{WORKSPACE}/state/state.json"), workspace_root) == (
        workspace_root / "state" / "state.json"
    )


def test_resolve_workspace_root_checks_child_directories_before_current_directory(
    tmp_path: Path,
) -> None:
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    child_workspace = cwd / "demo"
    child_workspace.mkdir()
    (child_workspace / WORKSPACE_MARKER).write_text("", encoding="utf-8")
    (cwd / WORKSPACE_MARKER).write_text("", encoding="utf-8")

    resolved = resolve_workspace_root(cwd=cwd, home=tmp_path / "home", env={})

    assert resolved == child_workspace.resolve()


def test_resolve_workspace_root_finds_workspace_in_ancestor_child_directory(
    tmp_path: Path,
) -> None:
    home = tmp_path / "home"
    home.mkdir()
    ancestor = tmp_path / "ancestor"
    ancestor.mkdir()
    workspace = ancestor / "demo"
    workspace.mkdir()
    (workspace / WORKSPACE_MARKER).write_text("", encoding="utf-8")
    nested = ancestor / "nested" / "child"
    nested.mkdir(parents=True)

    resolved = resolve_workspace_root(cwd=nested, home=home, env={})

    assert resolved == workspace.resolve()


def test_resolve_workspace_root_uses_home_as_last_search_base(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    workspace = home / "demo"
    workspace.mkdir()
    (workspace / WORKSPACE_MARKER).write_text("", encoding="utf-8")

    resolved = resolve_workspace_root(cwd=tmp_path / "other", home=home, env={})

    assert resolved == workspace.resolve()


def test_resolve_workspace_root_accepts_marker_without_config(tmp_path: Path) -> None:
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    workspace = cwd / "demo"
    workspace.mkdir()
    (workspace / WORKSPACE_MARKER).write_text("", encoding="utf-8")

    resolved = resolve_workspace_root(cwd=cwd, home=tmp_path / "home", env={})

    assert resolved == workspace.resolve()


def test_resolve_workspace_root_skips_inaccessible_child_directory(
    monkeypatch, tmp_path: Path
) -> None:
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    blocked = cwd / "blocked"
    blocked.mkdir()
    workspace = cwd / "workspace"
    workspace.mkdir()
    (workspace / WORKSPACE_MARKER).write_text("", encoding="utf-8")

    original_is_dir = Path.is_dir

    def fake_is_dir(path: Path) -> bool:
        if path == blocked:
            raise OSError("permission denied")
        return original_is_dir(path)

    monkeypatch.setattr(Path, "is_dir", fake_is_dir)

    resolved = resolve_workspace_root(cwd=cwd, home=tmp_path / "home", env={})

    assert resolved == workspace.resolve()


def test_resolve_workspace_root_error_lists_checked_candidates(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    (cwd / "child-a").mkdir()
    (home / "child-b").mkdir()

    try:
        resolve_workspace_root(cwd=cwd, home=home, env={})
    except RuntimeError as exc:
        message = str(exc)
    else:
        raise AssertionError("resolve_workspace_root should have failed")

    assert "Unable to locate keywharf workspace." in message
    assert str((cwd / "child-a").resolve()) in message
    assert str(cwd.resolve()) in message
    assert str((home / "child-b").resolve()) in message
