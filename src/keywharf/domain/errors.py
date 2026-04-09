"""Project-specific error types."""

from __future__ import annotations


class KeywharfError(Exception):
    """Base exception carrying a CLI-oriented exit code."""

    def __init__(self, message: str, *, exit_code: int = 1) -> None:
        super().__init__(message)
        self.exit_code = exit_code


class PrivilegeRequiredError(KeywharfError):
    """Raised when one mutating operation needs elevated privileges."""
