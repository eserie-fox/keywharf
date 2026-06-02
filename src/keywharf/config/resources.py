"""Package-resource and template loaders."""

from __future__ import annotations

import json
from importlib import resources
from pathlib import Path
from typing import Any

from jinja2 import Environment, PackageLoader, select_autoescape

_PKG_SCHEME = "pkg://"
_TEMPLATE_ENVIRONMENT = Environment(
    loader=PackageLoader("keywharf", "templates"),
    autoescape=select_autoescape(default_for_string=False, disabled_extensions=("j2",)),
    trim_blocks=True,
    lstrip_blocks=True,
)


def read_text(spec: str | Path, *, encoding: str = "utf-8") -> str:
    """Read text from a filesystem path or one ``pkg://`` resource spec."""

    if isinstance(spec, Path):
        return spec.read_text(encoding=encoding)

    text = str(spec)
    if not text.startswith(_PKG_SCHEME):
        return Path(text).expanduser().read_text(encoding=encoding)

    payload = text[len(_PKG_SCHEME) :]
    parts = [part for part in payload.split("/") if part]
    if len(parts) < 2:
        raise ValueError(f"invalid package resource spec: {spec}")

    package = parts[0]
    resource_parts = parts[1:]
    return resources.files(package).joinpath(*resource_parts).read_text(encoding=encoding)


def read_json(spec: str | Path) -> Any:
    """Read one JSON payload from filesystem or package resources."""

    return json.loads(read_text(spec))


def read_json_mapping(spec: str | Path) -> dict[str, Any]:
    """Read one JSON object payload."""

    payload = read_json(spec)
    if not isinstance(payload, dict):
        raise ValueError(f"JSON resource root must be an object: {spec}")
    return payload


def render_template(template_name: str, /, **context: object) -> str:
    """Render one package-shipped Jinja template."""

    return _TEMPLATE_ENVIRONMENT.get_template(template_name).render(**context)
