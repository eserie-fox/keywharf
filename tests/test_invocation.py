from __future__ import annotations

from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

from keywharf.commands._invocation import build_command_invocation

RUNNER = CliRunner()


@pytest.fixture
def invocation_app():
    app = typer.Typer()
    repo = typer.Typer()
    app.add_typer(repo, name="repo")
    captured = []
    overrides = {}

    @app.callback()
    def configure(ctx: typer.Context, config: Path = typer.Option(..., "--config")):
        ctx.obj = config

    @repo.command("select")
    def select(
        ctx: typer.Context,
        query: str,
        names: list[str] | None = typer.Option(None, "--name"),
        comment: str | None = typer.Option(None, "--comment"),
        force: bool = typer.Option(True, "--force/--no-force"),
        directory: Path = typer.Option(Path("."), "--directory"),
        sudo: bool = typer.Option(False, "--sudo"),
    ):
        parameters = {
            "config": ctx.obj,
            "query": query,
            "names": names,
            "comment": comment,
            "force": force,
            "directory": directory,
            "sudo": sudo,
        }
        captured.append((parameters, build_command_invocation(ctx, overrides=overrides)))

    return app, captured, overrides


@pytest.mark.parametrize(
    "query, comment",
    [("demo", "--sudo"), ("-demo", "--"), ("--sudo", None), ("--", None)],
)
def test_sudo_retry_round_trips_parsed_parameters(invocation_app, tmp_path, query, comment):
    app, captured, _ = invocation_app
    arguments = ["--config", str(tmp_path / "config.json"), "repo", "select"]
    arguments.extend(["--name", "dev", "--name", "work", "--no-force"])
    if comment is not None:
        arguments.extend(["--comment", comment])
    arguments.extend(["--", query])
    result = RUNNER.invoke(app, arguments)
    assert result.exit_code == 0, result.exception

    parameters, invocation = captured[0]
    retry = invocation.with_sudo_flag().with_sudo_flag()
    assert len(retry.argv) == len(invocation.argv) + 1
    result = RUNNER.invoke(app, retry.argv)
    assert result.exit_code == 0, result.exception
    assert captured[1][0] == {**parameters, "sudo": True}


def test_retry_applies_parameter_overrides(invocation_app, tmp_path):
    app, captured, overrides = invocation_app
    overrides["directory"] = tmp_path / "target"
    result = RUNNER.invoke(
        app, ["--config", str(tmp_path / "config.json"), "repo", "select", "demo"]
    )
    assert result.exit_code == 0, result.exception

    parameters, invocation = captured[0]
    result = RUNNER.invoke(app, invocation.argv)
    assert result.exit_code == 0, result.exception
    assert captured[1][0] == {**parameters, **overrides}
