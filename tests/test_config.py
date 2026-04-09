from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from keywharf.config.merge import config_deep_merge
from keywharf.config.models import ManagerConfig
from tests.support import write_json


def test_manager_config_from_defaults_reads_package_defaults() -> None:
    config = ManagerConfig.from_defaults()

    assert config.ssh_key_remote_repo == "git@example.com:org/keys.git"
    assert config.ssh_key_local_repo == "%{DATA_ROOT}/repos/keys"
    assert config.ssh_dir == "~/.ssh"
    assert config.managed_config_path is None
    assert config.managed_keys_dir is None
    assert config.state_path == "%{DATA_ROOT}/state/state.json"


def test_manager_config_from_file_merges_defaults_and_override(tmp_path: Path) -> None:
    config_path = write_json(tmp_path / "config.json", {"ssh_dir": "~/custom-ssh"})

    config = ManagerConfig.from_file(config_path)

    assert config.ssh_dir == "~/custom-ssh"
    assert config.ssh_key_local_repo == "%{DATA_ROOT}/repos/keys"


def test_manager_config_from_mapping_merges_defaults_and_override() -> None:
    config = ManagerConfig.from_mapping({"ssh_key_remote_repo": "git@example.com:alt/keys.git"})

    assert config.ssh_key_remote_repo == "git@example.com:alt/keys.git"
    assert config.state_path == "%{DATA_ROOT}/state/state.json"


def test_config_deep_merge_recurse_and_replace_non_mappings() -> None:
    merged = config_deep_merge(
        {"nested": {"a": 1}, "items": [1], "value": "old"},
        {"nested": {"b": 2}, "items": [2], "value": "new"},
    )

    assert merged == {"nested": {"a": 1, "b": 2}, "items": [2], "value": "new"}


def test_manager_config_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        ManagerConfig.from_mapping({"unknown": "value"})

