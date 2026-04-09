from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_json(path: Path, payload: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def make_data_root(base: Path, *, marker_name: str = "SSH_MANAGER_DATA_ROOT") -> Path:
    data_root = base / "data-root"
    data_root.mkdir(parents=True, exist_ok=True)
    (data_root / marker_name).write_text("", encoding="utf-8")
    return data_root


def manager_config_payload(
    *,
    ssh_key_remote_repo: str = "git@example.com:org/keys.git",
    ssh_key_local_repo: str = "%{DATA_ROOT}/repos/keys",
    ssh_dir: str = "%{DATA_ROOT}/ssh-home",
) -> dict[str, Any]:
    return {
        "ssh_key_remote_repo": ssh_key_remote_repo,
        "ssh_key_local_repo": ssh_key_local_repo,
        "ssh_dir": ssh_dir,
    }


def write_manager_config(
    config_path: Path,
    *,
    ssh_key_remote_repo: str = "git@example.com:org/keys.git",
    ssh_key_local_repo: str = "%{DATA_ROOT}/repos/keys",
    ssh_dir: str = "%{DATA_ROOT}/ssh-home",
) -> Path:
    return write_json(
        config_path,
        manager_config_payload(
            ssh_key_remote_repo=ssh_key_remote_repo,
            ssh_key_local_repo=ssh_key_local_repo,
            ssh_dir=ssh_dir,
        ),
    )


def remote_repo_payload(
    *,
    identity_file: str = "keys/id_demo",
) -> list[dict[str, Any]]:
    return [
        {
            "ServerName": "demo",
            "Comment": "demo host",
            "Endpoint": [
                {
                    "HostName": "example.com",
                    "Port": 22,
                    "Comment": "public",
                }
            ],
            "Authentication": [
                {
                    "User": "fox",
                    "IdentityFile": identity_file,
                    "Comment": "main key",
                }
            ],
            "ExtraConfig": [
                {
                    "Key": "ProxyJump",
                    "Value": "bastion",
                    "Comment": "optional hop",
                }
            ],
        }
    ]


def write_remote_repo_config(repo_root: Path, payload: list[dict[str, Any]] | None = None) -> Path:
    repo_root.mkdir(parents=True, exist_ok=True)
    return write_json(repo_root / "config.json", payload or remote_repo_payload())


def write_identity_file(repo_root: Path, relative_path: str = "keys/id_demo") -> Path:
    path = repo_root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("PRIVATE KEY", encoding="utf-8")
    return path


def write_local_ssh_config(ssh_dir: Path, content: str) -> Path:
    ssh_dir.mkdir(parents=True, exist_ok=True)
    path = ssh_dir / "config"
    path.write_text(content, encoding="utf-8")
    return path
