from __future__ import annotations

import json
from importlib import resources


def test_manager_defaults_resource_is_readable() -> None:
    payload = json.loads(
        resources.files("ssh_manager").joinpath("config_defaults", "manager.json").read_text(encoding="utf-8")
    )

    assert payload["ssh_key_remote_repo"] == "git@example.com:org/keys.git"
    assert payload["managed_config_path"] is None


def test_init_state_template_resource_is_readable() -> None:
    payload = json.loads(
        resources.files("ssh_manager").joinpath("templates", "init_state.json").read_text(encoding="utf-8")
    )

    assert payload == {"version": 1, "selected_hosts": []}

