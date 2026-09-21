"""Human comment representation and reserved managed-metadata policy."""

from __future__ import annotations


def normalize_comment(value: object | None) -> str | None:
    """Use LF, trim outer whitespace, and preserve every interior character and blank line."""
    if value is None:
        return None
    text = str(value).replace("\r\n", "\n").replace("\r", "\n").strip()
    return text or None


def is_reserved_comment_line(line: str) -> bool:
    return line.strip().casefold().startswith("keywharf-owner")


def validate_comment(comment: object | None) -> None:
    text = normalize_comment(comment)
    if text is None:
        return
    for lineno, line in enumerate(text.splitlines(), start=1):
        if is_reserved_comment_line(line):
            raise ValueError(
                f"Comment line {lineno} uses reserved keywharf-owner metadata; "
                "human comments cannot start with this prefix."
            )
