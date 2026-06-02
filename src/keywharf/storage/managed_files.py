"""Storage helpers for manager-owned SSH config and key material."""

from __future__ import annotations

import fnmatch
import os
import shlex
from pathlib import Path

from keywharf.config.resolver import ResolvedManagerConfig
from keywharf.config.resources import render_template
from keywharf.domain.results import IncludeInstallResult
from keywharf.storage.ssh_files import read_ssh_config, write_ssh_config

KEYWHARF_INCLUDE_COMMENT = "# Added by keywharf"
INCLUDE_BLOCK_TEMPLATE = "include_block.j2"


def read_managed_config(config: ResolvedManagerConfig) -> str:
    return read_ssh_config(config.managed_config_path)


def write_managed_config(
    config: ResolvedManagerConfig,
    content: str,
    *,
    backup: bool = True,
) -> None:
    write_ssh_config(config.managed_config_path, content, backup=backup)


def managed_key_path(
    config: ResolvedManagerConfig,
    host_name: str,
    original_identity_file: str,
) -> Path:
    return config.managed_key_path_for(host_name, original_identity_file)


def include_line_for_config(
    config: ResolvedManagerConfig,
    *,
    home: Path | None = None,
) -> str:
    return f"Include {_format_include_path(config.managed_config_path, home=home)}"


def include_is_installed(config: ResolvedManagerConfig) -> bool:
    main_config_path = config.main_config_path
    if not main_config_path.exists():
        return False
    return _content_has_include(
        main_config_path.read_text(encoding="utf-8"),
        main_config_path=main_config_path,
        managed_config_path=config.managed_config_path,
    )


def install_include(
    config: ResolvedManagerConfig,
    *,
    dry_run: bool = False,
    backup: bool = True,
) -> IncludeInstallResult:
    main_config_path = config.main_config_path
    include_line = include_line_for_config(config)

    if main_config_path.exists():
        current_content = main_config_path.read_text(encoding="utf-8")
        if _content_has_include(
            current_content,
            main_config_path=main_config_path,
            managed_config_path=config.managed_config_path,
        ):
            return IncludeInstallResult(
                main_config_path=main_config_path,
                managed_config_path=config.managed_config_path,
                include_line=include_line,
                already_present=True,
                changed=False,
                dry_run=dry_run,
                rendered_content=current_content,
            )
        new_content = _append_include_block(current_content, _render_include_block(include_line))
    else:
        new_content = _render_include_block(include_line)

    if not dry_run:
        write_ssh_config(main_config_path, new_content, backup=backup)

    return IncludeInstallResult(
        main_config_path=main_config_path,
        managed_config_path=config.managed_config_path,
        include_line=include_line,
        already_present=False,
        changed=True,
        dry_run=dry_run,
        rendered_content=new_content,
    )


def _render_include_block(include_line: str) -> str:
    return render_template(
        INCLUDE_BLOCK_TEMPLATE,
        include_comment=KEYWHARF_INCLUDE_COMMENT,
        include_line=include_line,
    )


def _append_include_block(existing_content: str, include_block: str) -> str:
    if not existing_content:
        return include_block
    if existing_content.endswith("\n\n"):
        return f"{existing_content}{include_block}"
    if existing_content.endswith("\n"):
        return f"{existing_content}\n{include_block}"
    return f"{existing_content}\n\n{include_block}"


def _content_has_include(
    content: str,
    *,
    main_config_path: Path,
    managed_config_path: Path,
) -> bool:
    target = managed_config_path.resolve().as_posix()
    for raw_line in content.splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue
        if raw_line[:1] in (" ", "\t"):
            continue
        if stripped.startswith("#"):
            continue
        keyword, separator, remainder = stripped.partition(" ")
        if keyword != "Include" or not separator:
            continue
        for pattern in _split_include_patterns(remainder):
            if _include_pattern_matches(
                pattern,
                main_config_path=main_config_path,
                managed_config_path=managed_config_path,
                normalized_target=target,
            ):
                return True
    return False


def _split_include_patterns(remainder: str) -> list[str]:
    try:
        return [item for item in shlex.split(remainder, comments=False, posix=True) if item]
    except ValueError:
        return [item for item in remainder.split() if item]


def _include_pattern_matches(
    pattern: str,
    *,
    main_config_path: Path,
    managed_config_path: Path,
    normalized_target: str,
) -> bool:
    normalized_pattern = _normalize_include_pattern(pattern, base_dir=main_config_path.parent)
    if any(char in normalized_pattern for char in "*?["):
        return fnmatch.fnmatch(normalized_target, normalized_pattern.replace("\\", "/"))
    return Path(normalized_pattern).resolve() == managed_config_path.resolve()


def _normalize_include_pattern(pattern: str, *, base_dir: Path) -> str:
    expanded = os.path.expandvars(os.path.expanduser(pattern))
    if not os.path.isabs(expanded):
        expanded = os.path.join(base_dir.as_posix(), expanded)
    return os.path.normpath(expanded).replace("\\", "/")


def _format_include_path(path: Path, *, home: Path | None = None) -> str:
    home_path = (home or Path.home()).expanduser().resolve()
    candidate = path.expanduser().resolve()
    try:
        relative = candidate.relative_to(home_path)
    except ValueError:
        return candidate.as_posix()
    return Path("~").joinpath(relative).as_posix()
