from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from keywharf.cli import app
from keywharf.services.render import render_selected_state
from tests.support import (
    load_config,
    make_data_root,
    remote_repo_payload,
    selection_payload,
    state_payload,
    write_identity_file,
    write_managed_ssh_config,
    write_manager_config,
    write_remote_repo_config,
    write_state_file,
)


RUNNER = CliRunner()


def test_local_list_reports_applied_pending_and_orphaned(tmp_path: Path) -> None:
    data_root = make_data_root(tmp_path)
    config_path = write_manager_config(data_root / "config.json")
    config = load_config(config_path, data_root=data_root)
    repo_root = data_root / "repos" / "keys"
    write_identity_file(repo_root, "keys/id_demo")
    write_identity_file(repo_root, "keys/id_other")
    write_remote_repo_config(
        repo_root,
        payload=[
            remote_repo_payload(server_name="demo", endpoint_name="public", auth_name="home")[0],
            remote_repo_payload(server_name="other", endpoint_name="public", auth_name="home", identity_file="keys/id_other")[0],
        ],
    )
    write_state_file(
        config.state_path,
        payload=state_payload(
            selected_hosts=[
                selection_payload(server_name="demo", endpoint_name="public", authentication_name="home")
            ]
        ),
    )
    write_managed_ssh_config(config.managed_config_path, render_selected_state(config).content)
    write_state_file(
        config.state_path,
        payload=state_payload(
            selected_hosts=[
                selection_payload(server_name="demo", endpoint_name="public", authentication_name="home"),
                selection_payload(server_name="other", endpoint_name="public", authentication_name="home"),
            ]
        ),
    )
    config.managed_config_path.write_text(
        config.managed_config_path.read_text(encoding="utf-8")
        + "\nHost orphaned\n  HostName orphan.example.com\n",
        encoding="utf-8",
    )

    result = RUNNER.invoke(app, ["--config", str(config_path), "local", "list", "--json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    statuses = {item["server_name"]: item["status"] for item in payload}
    assert statuses["demo"] == "applied"
    assert statuses["other"] == "pending"
    assert statuses["orphaned"] == "orphaned"


def test_local_show_includes_desired_and_current_blocks(tmp_path: Path) -> None:
    data_root = make_data_root(tmp_path)
    config_path = write_manager_config(data_root / "config.json")
    config = load_config(config_path, data_root=data_root)
    repo_root = data_root / "repos" / "keys"
    write_identity_file(repo_root)
    write_remote_repo_config(repo_root, payload=remote_repo_payload(endpoint_name="public", auth_name="home"))
    write_state_file(
        config.state_path,
        payload=state_payload(
            selected_hosts=[
                selection_payload(server_name="demo", endpoint_name="public", authentication_name="home")
            ]
        ),
    )
    write_managed_ssh_config(
        config.managed_config_path,
        "# This file is managed by keywharf\n\nHost demo\n  HostName example.com\n",
    )

    result = RUNNER.invoke(app, ["--config", str(config_path), "local", "show", "demo", "--json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["server_name"] == "demo"
    assert payload["desired_block"] is not None
    assert payload["current_block"] is not None
