"""Initialize a new keywharf workspace skeleton."""

from __future__ import annotations

from pathlib import Path

from keywharf.config.loader import load_resolved_manager_config
from keywharf.config.models import ManagerConfig
from keywharf.config.resources import read_text, render_template
from keywharf.domain.errors import KeywharfError
from keywharf.domain.results import InitResult
from keywharf.runtime.paths import WORKSPACE_MARKER
from keywharf.services.privilege import can_write_directory, can_write_file, root_owned_hint


EMPTY_STATE_RESOURCE_SPEC = "pkg://keywharf/templates/init_state.json"
WORKSPACE_README_TEMPLATE = "workspace_README.md.j2"
WORKSPACE_GITIGNORE_TEMPLATE = "workspace_gitignore.j2"


def resolve_init_paths(
    workspace_name: str,
    *,
    base_dir: Path | None = None,
    cwd: Path | None = None,
) -> tuple[Path, Path]:
    current_dir = (cwd or Path.cwd()).expanduser().resolve()
    resolved_base_dir = (base_dir or current_dir).expanduser().resolve()
    cleaned_name = workspace_name.strip()
    if not cleaned_name:
        raise KeywharfError("Workspace name must not be blank.", exit_code=2)
    workspace_root = (resolved_base_dir / cleaned_name).resolve()
    return workspace_root, (workspace_root / "config.json").resolve()


def initialize_workspace(
    workspace_name: str,
    *,
    base_dir: Path | None = None,
    cwd: Path | None = None,
    ssh_dir: str = "~/.ssh",
) -> InitResult:
    resolved_workspace_root, config_path = resolve_init_paths(
        workspace_name,
        base_dir=base_dir,
        cwd=cwd,
    )
    created_paths: list[Path] = []

    if resolved_workspace_root.exists():
        if not resolved_workspace_root.is_dir():
            raise KeywharfError(
                f"Workspace target exists but is not a directory: {resolved_workspace_root}"
            )
        if any(resolved_workspace_root.iterdir()):
            raise KeywharfError(
                f"Workspace target already exists and is not empty: {resolved_workspace_root}"
            )
    else:
        resolved_workspace_root.mkdir(parents=True, exist_ok=False)
        created_paths.append(resolved_workspace_root)

    generated_config = ManagerConfig.from_mapping(
        {
            "ssh_dir": ssh_dir,
        }
    )

    marker_path = resolved_workspace_root / WORKSPACE_MARKER
    marker_path.write_text("", encoding="utf-8")
    created_paths.append(marker_path)

    config_path.write_text(generated_config.model_dump_json(indent=2) + "\n", encoding="utf-8")
    created_paths.append(config_path)

    config = load_resolved_manager_config(config_path, workspace_root=resolved_workspace_root)

    for directory in (config.host_repo_path.parent, config.state_path.parent):
        directory.mkdir(parents=True, exist_ok=True)
        created_paths.append(directory)

    config.state_path.write_text(read_text(EMPTY_STATE_RESOURCE_SPEC), encoding="utf-8")
    created_paths.append(config.state_path)

    for path, content in (
        (
            resolved_workspace_root / "README.md",
            render_template(
                WORKSPACE_README_TEMPLATE,
                workspace_root=resolved_workspace_root.as_posix(),
                config_path=config_path.as_posix(),
                state_path=config.state_path.as_posix(),
                host_repo_path=config.host_repo_path.as_posix(),
                managed_config_path=config.managed_config_path.as_posix(),
                managed_keys_dir=config.managed_keys_dir.as_posix(),
                marker_name=WORKSPACE_MARKER,
            ),
        ),
        (
            resolved_workspace_root / ".gitignore",
            render_template(WORKSPACE_GITIGNORE_TEMPLATE),
        ),
    ):
        path.write_text(content, encoding="utf-8")
        created_paths.append(path)

    return InitResult(
        workspace_root=resolved_workspace_root,
        config_path=config_path,
        state_path=config.state_path,
        created_paths=created_paths,
    )


def analyze_init_root_requirements(
    workspace_name: str,
    *,
    base_dir: Path | None = None,
    cwd: Path | None = None,
) -> list[str]:
    """Return concrete privilege reasons for one init run."""

    resolved_workspace_root, config_path = resolve_init_paths(
        workspace_name,
        base_dir=base_dir,
        cwd=cwd,
    )
    marker_path = resolved_workspace_root / WORKSPACE_MARKER
    state_dir = resolved_workspace_root / "state"
    state_path = state_dir / "state.json"
    repos_dir = resolved_workspace_root / "repos"
    reasons: list[str] = []

    if not resolved_workspace_root.exists():
        if not can_write_directory(resolved_workspace_root):
            reasons.append(
                f"workspace target directory is not creatable by current user: {resolved_workspace_root}{root_owned_hint(resolved_workspace_root.parent)}"
            )
    elif not can_write_directory(resolved_workspace_root):
        reasons.append(
            f"workspace target directory is not writable by current user: {resolved_workspace_root}{root_owned_hint(resolved_workspace_root)}"
        )

    for directory, label in (
        (state_dir, "state directory"),
        (repos_dir, "repo directory"),
    ):
        if directory.exists():
            if not can_write_directory(directory):
                reasons.append(
                    f"{label} is not writable by current user: {directory}{root_owned_hint(directory)}"
                )
        elif not can_write_directory(directory):
            reasons.append(
                f"{label} is not creatable by current user: {directory}{root_owned_hint(directory.parent)}"
            )

    for path, label in (
        (marker_path, "workspace marker"),
        (config_path, "manager config"),
        (state_path, "state file"),
        (resolved_workspace_root / "README.md", "workspace README"),
        (resolved_workspace_root / ".gitignore", "workspace gitignore"),
    ):
        if not path.exists() and not can_write_file(path):
            reasons.append(
                f"{label} path is not writable by current user: {path}{root_owned_hint(path.parent)}"
            )

    return reasons
