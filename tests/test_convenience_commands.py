from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from keywharf.cli import app
from tests.support import (
    host_repo_payload,
    load_config,
    make_workspace,
    selection_payload,
    state_payload,
    write_host_repo_config,
    write_identity_file,
    write_manager_config,
    write_state_file,
)


RUNNER = CliRunner()


def _prepare_read_only_view_workspace(tmp_path: Path) -> Path:
    workspace_root = make_workspace(tmp_path)
    config_path = write_manager_config(workspace_root / "config.json")
    config = load_config(config_path, workspace_root=workspace_root)
    write_identity_file(config.host_repo_path)
    write_host_repo_config(
        config.host_repo_path,
        payload=host_repo_payload(endpoint_name="public", auth_name="home"),
    )
    write_state_file(
        config.state_path,
        payload=state_payload(
            selected_hosts=[
                selection_payload(
                    server_name="demo",
                    endpoint_name="public",
                    authentication_name="home",
                )
            ]
        ),
    )
    return config_path


def test_list_repo_facade_matches_repo_host_list(tmp_path: Path) -> None:
    config_path = _prepare_read_only_view_workspace(tmp_path)

    canonical = RUNNER.invoke(
        app,
        ["--config", str(config_path), "repo", "host", "list", "--json"],
    )
    facade = RUNNER.invoke(
        app,
        ["--config", str(config_path), "list", "repo", "--json"],
    )

    assert canonical.exit_code == 0, canonical.output
    assert facade.exit_code == canonical.exit_code
    assert facade.output == canonical.output


def test_show_repo_facade_matches_repo_host_show(tmp_path: Path) -> None:
    config_path = _prepare_read_only_view_workspace(tmp_path)

    canonical = RUNNER.invoke(
        app,
        ["--config", str(config_path), "repo", "host", "show", "demo", "--json"],
    )
    facade = RUNNER.invoke(
        app,
        ["--config", str(config_path), "show", "repo", "demo", "--json"],
    )

    assert canonical.exit_code == 0, canonical.output
    assert facade.exit_code == canonical.exit_code
    assert facade.output == canonical.output


def test_list_local_facade_matches_local_list(tmp_path: Path) -> None:
    config_path = _prepare_read_only_view_workspace(tmp_path)

    canonical = RUNNER.invoke(
        app,
        [
            "--config",
            str(config_path),
            "local",
            "list",
            "--pattern",
            "demo",
            "--json",
        ],
    )
    facade = RUNNER.invoke(
        app,
        [
            "--config",
            str(config_path),
            "list",
            "local",
            "--pattern",
            "demo",
            "--json",
        ],
    )

    assert canonical.exit_code == 0, canonical.output
    assert facade.exit_code == canonical.exit_code
    assert facade.output == canonical.output


def test_show_local_facade_matches_local_show(tmp_path: Path) -> None:
    config_path = _prepare_read_only_view_workspace(tmp_path)

    canonical = RUNNER.invoke(
        app,
        ["--config", str(config_path), "local", "show", "demo", "--json"],
    )
    facade = RUNNER.invoke(
        app,
        ["--config", str(config_path), "show", "local", "demo", "--json"],
    )

    assert canonical.exit_code == 0, canonical.output
    assert facade.exit_code == canonical.exit_code
    assert facade.output == canonical.output


def test_facade_targets_are_limited_and_help_mentions_canonical_paths() -> None:
    invalid = RUNNER.invoke(app, ["list", "endpoint"])

    assert invalid.exit_code != 0
    assert "No such command 'endpoint'" in invalid.output

    list_help = RUNNER.invoke(app, ["list", "--help"])
    show_help = RUNNER.invoke(app, ["show", "--help"])

    assert list_help.exit_code == 0
    assert "Convenience read-only commands" in list_help.output
    assert "repo" in list_help.output
    assert "local" in list_help.output
    assert "repo host list" in list_help.output
    assert "local list" in list_help.output

    assert show_help.exit_code == 0
    assert "Convenience read-only commands" in show_help.output
    assert "repo" in show_help.output
    assert "local" in show_help.output
    assert "repo host show <server>" in show_help.output
    assert "local show <server>" in show_help.output
