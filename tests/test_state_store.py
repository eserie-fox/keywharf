from __future__ import annotations

from pathlib import Path

import pytest

from keywharf.domain.errors import KeywharfError
from keywharf.domain.models import LocalState, SelectedHostState
from keywharf.storage.state_store import load_state, save_state
from tests.support import load_config, make_workspace, write_manager_config, write_state_file


def test_state_store_round_trip_is_atomic_and_sorted(tmp_path: Path) -> None:
    workspace_root = make_workspace(tmp_path)
    config_path = write_manager_config(workspace_root / "config.json")
    config = load_config(config_path, workspace_root=workspace_root)
    state = LocalState(
        selected_hosts=[
            SelectedHostState(server_name="zeta"),
            SelectedHostState(server_name="alpha"),
        ]
    )

    save_state(config, state)
    loaded = load_state(config)

    assert [item.server_name for item in loaded.selected_hosts] == ["alpha", "zeta"]
    assert not config.state_path.with_name("state.json.tmp").exists()


def test_state_store_rejects_unknown_schema_version(tmp_path: Path) -> None:
    workspace_root = make_workspace(tmp_path)
    config_path = write_manager_config(workspace_root / "config.json")
    config = load_config(config_path, workspace_root=workspace_root)
    write_state_file(config.state_path, payload={"version": 99, "selected_hosts": []})

    with pytest.raises(KeywharfError):
        load_state(config)
