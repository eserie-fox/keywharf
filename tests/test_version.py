from __future__ import annotations

import tomllib
from pathlib import Path

from ssh_manager import __version__
from ssh_manager.version import __version__ as module_version


def test_version_is_single_sourced_from_version_module() -> None:
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert pyproject["project"]["dynamic"] == ["version"]
    assert "version" not in pyproject["project"]
    assert pyproject["tool"]["setuptools"]["dynamic"]["version"]["attr"] == "ssh_manager.version.__version__"
    assert __version__ == module_version

