from __future__ import annotations

import json
from pathlib import Path

import pytest

from ssh_manager.domain.errors import SSHManagerError
from ssh_manager.domain.models import LocalState, SelectedHostState
from ssh_manager.runtime.config import load_manager_config
from ssh_manager.storage.state_store import load_state, save_state
from tests.support import make_data_root, write_manager_config, write_state_file


def test_load_state_returns_empty_when_file_missing(tmp_path: Path) -> None:
    data_root = make_data_root(tmp_path)
    config_path = write_manager_config(data_root / "config.json")
    config = load_manager_config(config_path, data_root=data_root)

    state = load_state(config)

    assert state.selected_hosts == []


def test_save_state_writes_atomic_json_payload(tmp_path: Path) -> None:
    data_root = make_data_root(tmp_path)
    config_path = write_manager_config(data_root / "config.json")
    config = load_manager_config(config_path, data_root=data_root)
    state = LocalState(
        selected_hosts=[
            SelectedHostState(
                server_name="demo",
                endpoint_name="public",
                authentication_name="home",
            )
        ]
    )

    save_state(config, state)

    payload = json.loads(config.state_path.read_text(encoding="utf-8"))
    assert payload["selected_hosts"][0]["server_name"] == "demo"
    assert not config.state_path.with_name("state.json.tmp").exists()


def test_load_state_rejects_unknown_version(tmp_path: Path) -> None:
    data_root = make_data_root(tmp_path)
    config_path = write_manager_config(data_root / "config.json")
    config = load_manager_config(config_path, data_root=data_root)
    write_state_file(
        config.state_path,
        payload={
            "version": 99,
            "selected_hosts": [],
        },
    )

    with pytest.raises(SSHManagerError):
        load_state(config)
