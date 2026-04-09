from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from ssh_manager.cli import app
from ssh_manager.runtime.config import load_manager_config
from tests.support import make_data_root, write_manager_config, write_state_file


RUNNER = CliRunner()


def test_init_creates_minimal_workspace_skeleton(tmp_path: Path) -> None:
    data_root = tmp_path / "workspace"
    ssh_dir = data_root / "ssh-home"

    result = RUNNER.invoke(
        app,
        ["init", "--data-root", str(data_root), "--ssh-dir", str(ssh_dir)],
    )

    assert result.exit_code == 0, result.output
    assert (data_root / "SSH_MANAGER_DATA_ROOT").exists()
    assert (data_root / "config.json").exists()
    assert (data_root / "state" / "state.json").exists()

    config = load_manager_config(data_root / "config.json", data_root=data_root)
    assert config.managed_config_path.parent.exists()
    assert config.managed_keys_dir.exists()
    assert config.ssh_key_local_repo.parent.exists()
    payload = json.loads((data_root / "state" / "state.json").read_text(encoding="utf-8"))
    assert payload["selected_hosts"] == []


def test_init_does_not_overwrite_existing_config_or_state(tmp_path: Path) -> None:
    data_root = make_data_root(tmp_path)
    config_path = write_manager_config(
        data_root / "config.json",
        ssh_key_remote_repo="git@example.com:org/custom.git",
    )
    state_path = write_state_file(
        data_root / "state" / "state.json",
        payload={
            "version": 1,
            "selected_hosts": [
                {
                    "server_name": "demo",
                    "endpoint_name": "public",
                    "authentication_name": "home",
                }
            ],
        },
    )
    before_config = config_path.read_text(encoding="utf-8")
    before_state = state_path.read_text(encoding="utf-8")

    result = RUNNER.invoke(app, ["init", "--data-root", str(data_root)])

    assert result.exit_code == 0, result.output
    assert config_path.read_text(encoding="utf-8") == before_config
    assert state_path.read_text(encoding="utf-8") == before_state
