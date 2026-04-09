from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from keywharf.cli import app
from tests.support import load_config, make_data_root, read_json, write_manager_config, write_state_file


RUNNER = CliRunner()


def test_init_creates_workspace_from_package_resources(tmp_path: Path) -> None:
    data_root = tmp_path / "workspace"
    ssh_dir = data_root / "ssh-home"

    result = RUNNER.invoke(app, ["--data-root", str(data_root), "init", "--ssh-dir", str(ssh_dir)])

    assert result.exit_code == 0, result.output
    assert (data_root / "KEYWHARF_DATA_ROOT").exists()
    assert (data_root / "config.json").exists()
    assert (data_root / "state" / "state.json").exists()
    assert (data_root / "README.md").exists()
    assert (data_root / ".gitignore").exists()

    raw_config = read_json(data_root / "config.json")
    assert raw_config["ssh_key_remote_repo"] == "git@example.com:org/keys.git"
    assert raw_config["ssh_dir"] == str(ssh_dir)
    assert raw_config["managed_config_path"] is None
    assert raw_config["managed_keys_dir"] is None

    config = load_config(data_root / "config.json", data_root=data_root)
    assert config.managed_config_path.parent.exists()
    assert config.managed_keys_dir.exists()
    assert config.ssh_key_local_repo.parent.exists()
    assert read_json(data_root / "state" / "state.json") == {"version": 1, "selected_hosts": []}


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

    readme_path = data_root / "README.md"
    gitignore_path = data_root / ".gitignore"
    readme_path.write_text("custom readme\n", encoding="utf-8")
    gitignore_path.write_text("custom gitignore\n", encoding="utf-8")

    result = RUNNER.invoke(app, ["--data-root", str(data_root), "init"])

    assert result.exit_code == 0, result.output
    assert config_path.read_text(encoding="utf-8") == before_config
    assert state_path.read_text(encoding="utf-8") == before_state
    assert readme_path.read_text(encoding="utf-8") == "custom readme\n"
    assert gitignore_path.read_text(encoding="utf-8") == "custom gitignore\n"
