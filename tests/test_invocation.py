from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from keywharf.commands._invocation import build_command_invocation


@dataclass(slots=True)
class FakeParameterSource:
    name: str


@dataclass(slots=True)
class FakeArgument:
    name: str
    opts: list[str]
    expose_value: bool = True


@dataclass(slots=True)
class FakeOption:
    name: str
    opts: list[str]
    is_bool_flag: bool = False
    multiple: bool = False
    secondary_opts: list[str] | None = None
    expose_value: bool = True

    def __post_init__(self) -> None:
        if self.secondary_opts is None:
            self.secondary_opts = []


@dataclass(slots=True)
class FakeCommand:
    name: str
    params: list[Any]


class FakeContext:
    def __init__(
        self,
        *,
        command: FakeCommand,
        params: dict[str, Any],
        sources: dict[str, FakeParameterSource | None],
        info_name: str | None = None,
        parent: FakeContext | None = None,
    ) -> None:
        self.command = command
        self.params = params
        self.sources = sources
        self.info_name = info_name
        self.parent = parent

    def get_parameter_source(self, name: str) -> FakeParameterSource | None:
        return self.sources.get(name)


def test_build_command_invocation_serializes_typer_like_parameters_without_click_types(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "keywharf" / "config.json"
    root = FakeContext(
        command=FakeCommand(
            "keywharf",
            [
                FakeOption("config", ["--config", "-c"]),
                FakeOption("workspace", ["--workspace"]),
                FakeOption("install_completion", ["--install-completion"]),
            ],
        ),
        params={
            "config": config_path,
            "workspace": None,
            "install_completion": False,
        },
        sources={
            "config": FakeParameterSource("COMMANDLINE"),
            "workspace": FakeParameterSource("DEFAULT"),
            "install_completion": FakeParameterSource("COMMANDLINE"),
        },
    )
    select = FakeContext(
        command=FakeCommand(
            "select",
            [
                FakeArgument("server_name", ["server_name"]),
                FakeOption("endpoint", ["--endpoint"]),
                FakeOption("auth", ["--auth"]),
                FakeOption("tag", ["--tag"], multiple=True),
                FakeOption(
                    "force",
                    ["--force"],
                    is_bool_flag=True,
                    secondary_opts=["--no-force"],
                ),
                FakeOption("sudo", ["--sudo"], is_bool_flag=True),
            ],
        ),
        params={
            "server_name": "demo",
            "endpoint": "public",
            "auth": "home",
            "tag": ("alpha", "beta"),
            "force": False,
            "sudo": True,
        },
        sources={
            "endpoint": FakeParameterSource("COMMANDLINE"),
            "auth": FakeParameterSource("DEFAULT"),
            "tag": FakeParameterSource("COMMANDLINE"),
            "force": FakeParameterSource("COMMANDLINE"),
            "sudo": FakeParameterSource("COMMANDLINE"),
        },
        info_name="select",
        parent=root,
    )

    invocation = build_command_invocation(select)

    assert invocation.argv == [
        "--config",
        str(config_path),
        "select",
        "demo",
        "--endpoint",
        "public",
        "--tag",
        "alpha",
        "--tag",
        "beta",
        "--no-force",
    ]


def test_build_command_invocation_serializes_overridden_default_options(tmp_path: Path) -> None:
    default_directory = tmp_path / "default"
    override_directory = tmp_path / "override"
    root = FakeContext(
        command=FakeCommand("keywharf", []),
        params={},
        sources={},
    )
    init = FakeContext(
        command=FakeCommand(
            "init",
            [
                FakeArgument("workspace_name", ["workspace_name"]),
                FakeOption("directory", ["--directory"]),
            ],
        ),
        params={"workspace_name": "demo", "directory": default_directory},
        sources={
            "workspace_name": FakeParameterSource("COMMANDLINE"),
            "directory": FakeParameterSource("DEFAULT"),
        },
        info_name="init",
        parent=root,
    )

    invocation = build_command_invocation(
        init,
        overrides={"directory": override_directory},
    )

    assert invocation.argv == ["init", "demo", "--directory", str(override_directory)]
