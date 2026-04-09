from __future__ import annotations

import tomllib
from pathlib import Path

from keywharf.version import __version__ as module_version
import keywharf


def test_version_is_single_sourced_from_version_module() -> None:
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert pyproject["project"]["dynamic"] == ["version"]
    assert "version" not in pyproject["project"]
    assert pyproject["tool"]["setuptools"]["dynamic"]["version"]["attr"] == "keywharf.version.__version__"
    assert not hasattr(keywharf, "__version__")
    assert module_version
