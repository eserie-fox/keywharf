from __future__ import annotations

from pathlib import Path

from ssh_manager.runtime.config import load_manager_config
from ssh_manager.services.check import validate_remote_repo_config
from tests.support import (
    make_data_root,
    remote_repo_payload,
    write_identity_file,
    write_manager_config,
    write_remote_repo_config,
)


def test_check_is_pure_validation_when_config_is_valid(tmp_path: Path) -> None:
    data_root = make_data_root(tmp_path)
    config_path = data_root / "config.json"
    write_manager_config(config_path)
    repo_root = data_root / "repos" / "keys"
    write_identity_file(repo_root)
    remote_config_path = write_remote_repo_config(repo_root)
    before_text = remote_config_path.read_text(encoding="utf-8")
    before_stat = remote_config_path.stat()

    result = validate_remote_repo_config(load_manager_config(config_path, data_root=data_root))

    after_text = remote_config_path.read_text(encoding="utf-8")
    after_stat = remote_config_path.stat()
    assert result.ok is True
    assert result.errors == []
    assert before_text == after_text
    assert before_stat.st_mtime_ns == after_stat.st_mtime_ns
    assert not (repo_root / "config.json.bak").exists()


def test_check_reports_missing_identity_file_without_writing(tmp_path: Path) -> None:
    data_root = make_data_root(tmp_path)
    config_path = data_root / "config.json"
    write_manager_config(config_path)
    repo_root = data_root / "repos" / "keys"
    remote_config_path = write_remote_repo_config(
        repo_root,
        payload=remote_repo_payload(identity_file="keys/missing_key"),
    )
    before_text = remote_config_path.read_text(encoding="utf-8")

    result = validate_remote_repo_config(load_manager_config(config_path, data_root=data_root))

    assert result.ok is False
    assert any("missing_key" in error for error in result.errors)
    assert remote_config_path.read_text(encoding="utf-8") == before_text
    assert not (repo_root / "config.json.bak").exists()
