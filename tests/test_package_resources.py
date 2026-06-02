from __future__ import annotations

import json
import tomllib
from importlib import resources
from pathlib import Path

from keywharf.config.resources import render_template


def test_manager_defaults_resource_is_readable() -> None:
    payload = json.loads(
        resources.files("keywharf")
        .joinpath("config_defaults", "manager.json")
        .read_text(encoding="utf-8")
    )

    assert payload["host_repo_remote_url"] is None
    assert payload["host_repo_path"] == "%{WORKSPACE}/repo"
    assert payload["managed_config_path"] is None


def test_init_state_template_resource_is_readable() -> None:
    payload = json.loads(
        resources.files("keywharf")
        .joinpath("templates", "init_state.json")
        .read_text(encoding="utf-8")
    )

    assert payload == {"version": 1, "selected_hosts": []}


def test_jinja_templates_are_packaged_and_renderable() -> None:
    template_text = (
        resources.files("keywharf")
        .joinpath("templates", "include_block.j2")
        .read_text(encoding="utf-8")
    )

    assert "include_line" in template_text
    rendered = render_template(
        "include_block.j2",
        include_comment="# Added by keywharf",
        include_line="Include ~/.ssh/managed/keywharf.conf",
    )
    assert "# Added by keywharf" in rendered
    assert "Include ~/.ssh/managed/keywharf.conf" in rendered


def test_pyproject_package_data_includes_json_and_jinja_resources() -> None:
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    package_data = pyproject["tool"]["setuptools"]["package-data"]["keywharf"]

    assert "config_defaults/**/*.json" in package_data
    assert "templates/**/*.json" in package_data
    assert "templates/**/*.j2" in package_data
