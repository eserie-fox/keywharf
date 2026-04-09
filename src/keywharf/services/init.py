"""Initialize a minimal keywharf workspace skeleton from package resources."""

from __future__ import annotations

from pathlib import Path

from keywharf.config.loader import load_resolved_manager_config
from keywharf.config.models import ManagerConfig
from keywharf.config.resolver import resolve_manager_config
from keywharf.config.resources import read_text, render_template
from keywharf.domain.results import InitResult
from keywharf.runtime.paths import DATA_ROOT_MARKER
from keywharf.services.privilege import can_read_path, can_write_directory, can_write_file, root_owned_hint


EMPTY_STATE_RESOURCE_SPEC = "pkg://keywharf/templates/init_state.json"
WORKSPACE_README_TEMPLATE = "workspace_README.md.j2"
WORKSPACE_GITIGNORE_TEMPLATE = "workspace_gitignore.j2"


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
        elif not config_path.is_relative_to(resolved_data_root):
            raise RuntimeError(
                f"Absolute --config path {config_path} is outside data root {resolved_data_root}."
            )
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
    marker_path = resolved_data_root / DATA_ROOT_MARKER
    if marker_path.exists():
        preserved_paths.append(marker_path)
    else:
        marker_path.write_text("", encoding="utf-8")
        created_paths.append(marker_path)

    config_path.parent.mkdir(parents=True, exist_ok=True)
    generated_config = ManagerConfig.from_mapping(
        {
            "ssh_key_remote_repo": ssh_key_remote_repo,
            "ssh_dir": ssh_dir,
        }
    )
    if config_path.exists():
        preserved_paths.append(config_path)
    else:
        config_path.write_text(generated_config.model_dump_json(indent=2) + "\n", encoding="utf-8")
        created_paths.append(config_path)

    config = load_resolved_manager_config(config_path, data_root=resolved_data_root)

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
        config.state_path.write_text(read_text(EMPTY_STATE_RESOURCE_SPEC), encoding="utf-8")
        created_paths.append(config.state_path)

    for path, content in (
        (
            resolved_data_root / "README.md",
            render_template(
                WORKSPACE_README_TEMPLATE,
                data_root=resolved_data_root.as_posix(),
                config_path=config_path.as_posix(),
                state_path=config.state_path.as_posix(),
                managed_config_path=config.managed_config_path.as_posix(),
                managed_keys_dir=config.managed_keys_dir.as_posix(),
                marker_name=DATA_ROOT_MARKER,
            ),
        ),
        (
            resolved_data_root / ".gitignore",
            render_template(WORKSPACE_GITIGNORE_TEMPLATE),
        ),
    ):
        if path.exists():
            preserved_paths.append(path)
            continue
        path.write_text(content, encoding="utf-8")
        created_paths.append(path)

    return InitResult(
        data_root=resolved_data_root,
        config_path=config_path,
        state_path=config.state_path,
        created_paths=created_paths,
        preserved_paths=preserved_paths,
    )


def analyze_init_root_requirements(
    config_override: Path | None = None,
    *,
    data_root: Path | None = None,
    cwd: Path | None = None,
    ssh_key_remote_repo: str = "git@example.com:org/keys.git",
    ssh_dir: str = "~/.ssh",
) -> list[str]:
    """Return concrete privilege reasons for one init run."""

    resolved_data_root, config_path = resolve_init_paths(
        config_override,
        data_root=data_root,
        cwd=cwd,
    )
    marker_path = resolved_data_root / DATA_ROOT_MARKER
    reasons: list[str] = []

    if config_path.exists():
        if not can_read_path(config_path):
            reasons.append(
                f"manager config is not readable by current user: {config_path}{root_owned_hint(config_path)}"
            )
            return reasons
        resolved_config = load_resolved_manager_config(config_path, data_root=resolved_data_root)
    else:
        resolved_config = resolve_manager_config(
            ManagerConfig.from_mapping(
                {
                    "ssh_key_remote_repo": ssh_key_remote_repo,
                    "ssh_dir": ssh_dir,
                }
            ),
            config_path=config_path,
            data_root=resolved_data_root,
        )

    if not marker_path.exists() and not can_write_file(marker_path):
        reasons.append(
            f"data root marker path is not writable by current user: {marker_path}{root_owned_hint(marker_path.parent)}"
        )
    if not config_path.exists() and not can_write_file(config_path):
        reasons.append(
            f"manager config path is not writable by current user: {config_path}{root_owned_hint(config_path.parent)}"
        )

    for directory, label in (
        (resolved_data_root, "data root"),
        (resolved_config.ssh_key_local_repo.parent, "local repo parent"),
        (resolved_config.managed_config_path.parent, "managed config parent"),
        (resolved_config.managed_keys_dir, "managed keys directory"),
        (resolved_config.state_path.parent, "state directory"),
    ):
        if not directory.exists() and not can_write_directory(directory):
            reasons.append(
                f"{label} is not creatable by current user: {directory}{root_owned_hint(directory.parent)}"
            )
        elif directory.exists() and not can_write_directory(directory):
            reasons.append(
                f"{label} is not writable by current user: {directory}{root_owned_hint(directory)}"
            )

    for path, label in (
        (resolved_data_root / "README.md", "workspace README"),
        (resolved_data_root / ".gitignore", "workspace gitignore"),
        (resolved_config.state_path, "state file"),
    ):
        if not path.exists() and not can_write_file(path):
            reasons.append(
                f"{label} path is not writable by current user: {path}{root_owned_hint(path.parent)}"
            )

    return reasons
