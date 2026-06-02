from __future__ import annotations

import ast
import re
import sys
import tomllib
from pathlib import Path


def test_runtime_third_party_imports_are_declared_dependencies() -> None:
    declared_dependencies = {
        _normalize_distribution_name(_dependency_name(dependency))
        for dependency in _runtime_dependencies()
    }
    missing_dependencies = sorted(
        import_name
        for import_name in _runtime_third_party_imports()
        if _normalize_distribution_name(import_name) not in declared_dependencies
    )

    assert missing_dependencies == []


def test_runtime_dependencies_use_minimum_only_policy() -> None:
    runtime_dependencies = _runtime_dependencies()
    dependency_by_name = {
        _normalize_distribution_name(_dependency_name(dependency)): dependency
        for dependency in runtime_dependencies
    }

    capped_dependencies = [
        dependency
        for dependency in runtime_dependencies
        if any(operator in dependency for operator in ("<", "~=", "!="))
    ]

    assert capped_dependencies == []
    assert dependency_by_name["typer"] == "typer>=0.26"
    assert dependency_by_name["rich"] == "rich>=13.8"


def _runtime_dependencies() -> list[str]:
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    return list(pyproject["project"]["dependencies"])


def _runtime_third_party_imports() -> set[str]:
    imports: set[str] = set()
    for path in Path("src/keywharf").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".", maxsplit=1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                imports.add(node.module.split(".", maxsplit=1)[0])

    return {
        import_name
        for import_name in imports
        if import_name != "keywharf" and import_name not in sys.stdlib_module_names
    }


def _dependency_name(dependency: str) -> str:
    return re.split(r"[\[<>=!~; ]", dependency, maxsplit=1)[0]


def _normalize_distribution_name(name: str) -> str:
    return name.lower().replace("-", "_")
