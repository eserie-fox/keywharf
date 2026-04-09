"""Initialize a minimal ssh-manager workspace skeleton."""

from __future__ import annotations

import json
from pathlib import Path

from ssh_manager.domain.results import InitResult
from ssh_manager.runtime.config import default_manager_config_payload, load_manager_config
from ssh_manager.runtime.paths import PRIMARY_DATA_ROOT_MARKER
from ssh_manager.storage.state_store import empty_state, save_state


def resolve_init_paths(
    config_override: Path | None = None,
    *,
    data_root: Path | None = None,
    cwd: Path | None = None,
) -> tuple[Path, Path]:
    current_dir = (cwd or Path.cwd()).expanduser().resolve()
    resolved_data_root = (
        data_root.expanduser().resolve() if data_root is not None else current_dir
    )

    if config_override is None:
        return resolved_data_root, (resolved_data_root / "config.json").resolve()

    raw_config = Path(config_override).expanduser()
    if raw_config.is_absolute():
        config_path = raw_config.resolve()
        if data_root is None:
            resolved_data_root = config_path.parent
        return resolved_data_root, config_path

    return resolved_data_root, (resolved_data_root / raw_config).resolve()


def initialize_workspace(
    config_override: Path | None = None,
    *,
    data_root: Path | None = None,
    cwd: Path | None = None,
    ssh_key_remote_repo: str = "git@example.com:org/keys.git",
    ssh_dir: str = "~/.ssh",
) -> InitResult:
    resolved_data_root, config_path = resolve_init_paths(
        config_override,
        data_root=data_root,
        cwd=cwd,
    )
    created_paths: list[Path] = []
    preserved_paths: list[Path] = []

    resolved_data_root.mkdir(parents=True, exist_ok=True)
    marker_path = resolved_data_root / PRIMARY_DATA_ROOT_MARKER
    if marker_path.exists():
        preserved_paths.append(marker_path)
    else:
        marker_path.write_text("", encoding="utf-8")
        created_paths.append(marker_path)

    config_path.parent.mkdir(parents=True, exist_ok=True)
    if config_path.exists():
        preserved_paths.append(config_path)
    else:
        config_path.write_text(
            json.dumps(
                default_manager_config_payload(
                    ssh_key_remote_repo=ssh_key_remote_repo,
                    ssh_dir=ssh_dir,
                ),
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        created_paths.append(config_path)

    config = load_manager_config(config_path, data_root=resolved_data_root)

    for directory in (
        config.ssh_key_local_repo.parent,
        config.managed_config_path.parent,
        config.managed_keys_dir,
        config.state_path.parent,
    ):
        existed = directory.exists()
        directory.mkdir(parents=True, exist_ok=True)
        if existed:
            preserved_paths.append(directory)
        else:
            created_paths.append(directory)

    if config.state_path.exists():
        preserved_paths.append(config.state_path)
    else:
        save_state(config, empty_state())
        created_paths.append(config.state_path)

    return InitResult(
        data_root=resolved_data_root,
        config_path=config_path,
        state_path=config.state_path,
        created_paths=created_paths,
        preserved_paths=preserved_paths,
    )
