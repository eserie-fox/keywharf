from __future__ import annotations

from pathlib import Path


def test_public_docs_do_not_reference_removed_cli_or_config_terms() -> None:
    paths = [
        Path("README.md"),
        Path("docs/cli.md"),
        Path("docs/configuration.md"),
        Path("docs/architecture.md"),
        Path("src/keywharf/templates/workspace_README.md.j2"),
    ]
    text = "\n".join(path.read_text(encoding="utf-8") for path in paths)

    banned_snippets = [
        "--data-root",
        "KEYWHARF_DATA_ROOT",
        "%{DATA_ROOT}",
        "ssh_key_remote_repo",
        "ssh_key_local_repo",
        "keywharf pull",
        "keywharf remote",
        "`pull`",
        "`remote init`",
        "`remote host`",
    ]

    for snippet in banned_snippets:
        assert snippet not in text
