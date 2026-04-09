from __future__ import annotations

from pathlib import Path

import pytest

from ssh_manager.domain.errors import SSHManagerError
from ssh_manager.domain.models import LocalState, SelectedHostState
from ssh_manager.storage.state_store import load_state, save_state
from tests.support import load_config, make_data_root, write_manager_config, write_state_file


def test_state_store_round_trip_is_atomic_and_sorted(tmp_path: Path) -> None:
    data_root = make_data_root(tmp_path)
    config_path = write_manager_config(data_root / "config.json")
    config = load_config(config_path, data_root=data_root)
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
    data_root = make_data_root(tmp_path)
    config_path = write_manager_config(data_root / "config.json")
    config = load_config(config_path, data_root=data_root)
    write_state_file(config.state_path, payload={"version": 99, "selected_hosts": []})

    with pytest.raises(SSHManagerError):
        load_state(config)

