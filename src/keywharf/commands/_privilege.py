"""Privilege fail-fast and sudo re-exec helpers for mutating commands."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from keywharf.commands._invocation import CommandInvocation
from keywharf.domain.errors import PrivilegeRequiredError
from keywharf.services.privilege import can_read_path, root_owned_hint


def current_user_is_root() -> bool:
    geteuid = getattr(os, "geteuid", None)
    if geteuid is None:
        return False
    return geteuid() == 0


def maybe_reexec_with_sudo(
    *,
    operation: str,
    sudo_requested: bool,
    invocation: CommandInvocation,
    subject: str = "this operation",
) -> bool:
    """Immediately re-exec the full command through sudo when requested."""

    if current_user_is_root():
        return False
    if not sudo_requested:
        return False
    if shutil.which("sudo") is None:
        raise PrivilegeRequiredError(
            _format_privilege_message(
                operation,
                [],
                invocation,
                subject=subject,
                sudo_requested=True,
                sudo_available=False,
            )
        )
    os.execvp("sudo", invocation.sudo_exec_args())
    return True


def raise_for_missing_privileges(
    *,
    operation: str,
    reasons: list[str],
    invocation: CommandInvocation,
    subject: str = "this operation",
) -> None:
    """Raise one consistent fail-fast privilege error when reasons are present."""

    if current_user_is_root() or not reasons:
        return
    raise PrivilegeRequiredError(
        _format_privilege_message(operation, reasons, invocation, subject=subject)
    )


def unreadable_path_reason(path: Path, *, label: str) -> str | None:
    """Return one consistent unreadable-path reason for preflight checks."""

    if not path.exists() or can_read_path(path):
        return None
    return f"{label} is not readable by current user: {path}{root_owned_hint(path)}"


def _format_privilege_message(
    operation: str,
    reasons: list[str],
    invocation: CommandInvocation,
    *,
    subject: str = "this operation",
    sudo_requested: bool = False,
    sudo_available: bool = True,
) -> str:
    manual_command = invocation.display()
    retry_command = invocation.with_sudo_flag().display()
    lines = [f"{operation} requires elevated privileges for {subject}:"]
    if not reasons:
        lines[0] = lines[0][:-1] + "."
    else:
        lines.extend(f"- {reason}" for reason in reasons)
    if sudo_requested and not sudo_available:
        lines.append("`--sudo` was requested, but `sudo` is not available in PATH.")
        lines.append(f"Run this command as root instead: {manual_command}")
    else:
        lines.append(f"Retry with: {retry_command}")
        lines.append(f"Or run manually: sudo {manual_command}")
    return "\n".join(lines)
