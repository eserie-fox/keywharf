from __future__ import annotations

from pathlib import Path


def test_public_docs_use_current_workspace_and_repo_terms() -> None:
    paths = [
        Path("README.md"),
        Path("docs/cli.md"),
        Path("docs/configuration.md"),
        Path("docs/architecture.md"),
        Path("src/keywharf/templates/workspace_README.md.j2"),
    ]
    text = "\n".join(path.read_text(encoding="utf-8") for path in paths)

    assert "--workspace" in text
    assert "KEYWHARF_WORKSPACE" in text
    assert "%{WORKSPACE}" in text
    assert "%{WORKSPACE}/repo" in text
    assert "repo init" in text
    assert "repo sync" in text
    assert "repo host" in text
