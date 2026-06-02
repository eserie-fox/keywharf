from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from keywharf.cli import app
from tests.support import (
    host_repo_payload,
    host_shell_payload,
    load_config,
    make_workspace,
    read_json,
    selection_payload,
    state_payload,
    write_host_repo_config,
    write_identity_file,
    write_manager_config,
    write_state_file,
)

RUNNER = CliRunner()


def _force_interactive_selection(monkeypatch) -> None:
    monkeypatch.setattr(
        "keywharf.commands._selection_prompt._supports_interactive_selection",
        lambda: True,
    )


def test_select_writes_state_and_upserts_existing_selection(tmp_path: Path) -> None:
    workspace_root = make_workspace(tmp_path)
    config_path = write_manager_config(workspace_root / "config.json")
    config = load_config(config_path, workspace_root=workspace_root)
    host_repo_path = config.host_repo_path
    write_identity_file(host_repo_path, "keys/id_home")
    write_identity_file(host_repo_path, "keys/id_work")
    write_host_repo_config(
        host_repo_path,
        payload=host_repo_payload(
            endpoints=[
                {
                    "EndPointName": "public",
                    "HostName": "public.example.com",
                    "Port": 22,
                },
                {
                    "EndPointName": "private",
                    "HostName": "private.example.com",
                    "Port": 22,
                },
            ],
            authentications=[
                {
                    "AuthenticationName": "home",
                    "User": "fox",
                    "IdentityFile": "keys/id_home",
                },
                {
                    "AuthenticationName": "work",
                    "User": "fox",
                    "IdentityFile": "keys/id_work",
                },
            ],
        ),
    )

    first = RUNNER.invoke(
        app,
        [
            "--config",
            str(config_path),
            "select",
            "demo",
            "--endpoint",
            "public",
            "--auth",
            "home",
        ],
    )
    second = RUNNER.invoke(
        app,
        [
            "--config",
            str(config_path),
            "select",
            "demo",
            "--endpoint",
            "private",
            "--auth",
            "work",
        ],
    )

    assert first.exit_code == 0, first.output
    assert second.exit_code == 0, second.output
    assert read_json(config.state_path)["selected_hosts"] == [
        {
            "server_name": "demo",
            "endpoint_name": "private",
            "authentication_name": "work",
        }
    ]
    assert not config.managed_config_path.exists()


def test_select_uses_stable_names_not_array_indexes(tmp_path: Path) -> None:
    workspace_root = make_workspace(tmp_path)
    config_path = write_manager_config(workspace_root / "config.json")
    config = load_config(config_path, workspace_root=workspace_root)
    host_repo_path = config.host_repo_path
    write_identity_file(host_repo_path, "keys/id_home")
    write_identity_file(host_repo_path, "keys/id_work")
    write_host_repo_config(
        host_repo_path,
        payload=host_repo_payload(
            endpoints=[
                {
                    "EndPointName": "public",
                    "HostName": "public.example.com",
                    "Port": 22,
                },
                {
                    "EndPointName": "private",
                    "HostName": "private.example.com",
                    "Port": 22,
                },
            ],
            authentications=[
                {
                    "AuthenticationName": "home",
                    "User": "fox",
                    "IdentityFile": "keys/id_home",
                },
                {
                    "AuthenticationName": "work",
                    "User": "fox",
                    "IdentityFile": "keys/id_work",
                },
            ],
        ),
    )

    result = RUNNER.invoke(
        app,
        [
            "--config",
            str(config_path),
            "select",
            "demo",
            "--endpoint",
            "private",
            "--auth",
            "work",
        ],
    )

    assert result.exit_code == 0, result.output
    assert read_json(config.state_path)["selected_hosts"][0] == {
        "server_name": "demo",
        "endpoint_name": "private",
        "authentication_name": "work",
    }


def test_select_prompts_for_endpoint_and_auth_when_both_are_ambiguous(
    tmp_path: Path,
    monkeypatch,
) -> None:
    workspace_root = make_workspace(tmp_path)
    config_path = write_manager_config(workspace_root / "config.json")
    config = load_config(config_path, workspace_root=workspace_root)
    host_repo_path = config.host_repo_path
    write_identity_file(host_repo_path, "keys/id_home")
    write_identity_file(host_repo_path, "keys/id_work")
    write_host_repo_config(
        host_repo_path,
        payload=host_repo_payload(
            endpoints=[
                {
                    "EndPointName": "public",
                    "HostName": "public.example.com",
                    "Port": 22,
                    "Comment": "public",
                },
                {
                    "EndPointName": "private",
                    "HostName": "private.example.com",
                    "Port": 2200,
                    "Comment": "private",
                },
            ],
            authentications=[
                {
                    "AuthenticationName": "home",
                    "User": "fox",
                    "IdentityFile": "keys/id_home",
                    "Comment": "home key",
                },
                {
                    "AuthenticationName": "work",
                    "User": "fox-work",
                    "IdentityFile": "keys/id_work",
                    "Comment": "work key",
                },
            ],
        ),
    )
    _force_interactive_selection(monkeypatch)

    result = RUNNER.invoke(
        app,
        ["--config", str(config_path), "select", "demo"],
        input="2\n1\n",
    )

    assert result.exit_code == 0, result.output
    assert "Select endpoint for 'demo':" in result.output
    assert "1. public | public.example.com:22 | public" in result.output
    assert "2. private | private.example.com:2200 | private" in result.output
    assert "Select authentication for 'demo':" in result.output
    assert "1. home | user=fox | identity=keys/id_home | home key" in result.output
    assert "2. work | user=fox-work | identity=keys/id_work | work key" in result.output
    assert read_json(config.state_path)["selected_hosts"] == [
        {
            "server_name": "demo",
            "endpoint_name": "private",
            "authentication_name": "home",
        }
    ]


def test_select_prompts_only_for_endpoint_when_auth_is_singleton(
    tmp_path: Path,
    monkeypatch,
) -> None:
    workspace_root = make_workspace(tmp_path)
    config_path = write_manager_config(workspace_root / "config.json")
    config = load_config(config_path, workspace_root=workspace_root)
    host_repo_path = config.host_repo_path
    write_identity_file(host_repo_path, "keys/id_home")
    write_host_repo_config(
        host_repo_path,
        payload=host_repo_payload(
            endpoints=[
                {
                    "EndPointName": "public",
                    "HostName": "public.example.com",
                    "Port": 22,
                },
                {
                    "EndPointName": "private",
                    "HostName": "private.example.com",
                    "Port": 2200,
                },
            ],
            authentications=[
                {
                    "AuthenticationName": "home",
                    "User": "fox",
                    "IdentityFile": "keys/id_home",
                }
            ],
        ),
    )
    _force_interactive_selection(monkeypatch)

    result = RUNNER.invoke(
        app,
        ["--config", str(config_path), "select", "demo"],
        input="2\n",
    )

    assert result.exit_code == 0, result.output
    assert "Select endpoint for 'demo':" in result.output
    assert "Select authentication for 'demo':" not in result.output
    assert read_json(config.state_path)["selected_hosts"] == [
        {
            "server_name": "demo",
            "endpoint_name": "private",
            "authentication_name": "home",
        }
    ]


def test_select_prompts_only_for_auth_when_endpoint_is_singleton(
    tmp_path: Path,
    monkeypatch,
) -> None:
    workspace_root = make_workspace(tmp_path)
    config_path = write_manager_config(workspace_root / "config.json")
    config = load_config(config_path, workspace_root=workspace_root)
    host_repo_path = config.host_repo_path
    write_identity_file(host_repo_path, "keys/id_home")
    write_identity_file(host_repo_path, "keys/id_work")
    write_host_repo_config(
        host_repo_path,
        payload=host_repo_payload(
            endpoints=[{"EndPointName": "public", "HostName": "public.example.com", "Port": 22}],
            authentications=[
                {
                    "AuthenticationName": "home",
                    "User": "fox",
                    "IdentityFile": "keys/id_home",
                },
                {
                    "AuthenticationName": "work",
                    "User": "fox-work",
                    "IdentityFile": "keys/id_work",
                },
            ],
        ),
    )
    _force_interactive_selection(monkeypatch)

    result = RUNNER.invoke(
        app,
        ["--config", str(config_path), "select", "demo"],
        input="2\n",
    )

    assert result.exit_code == 0, result.output
    assert "Select endpoint for 'demo':" not in result.output
    assert "Select authentication for 'demo':" in result.output
    assert read_json(config.state_path)["selected_hosts"] == [
        {
            "server_name": "demo",
            "endpoint_name": "public",
            "authentication_name": "work",
        }
    ]


def test_select_single_endpoint_and_auth_succeeds_without_prompt(
    tmp_path: Path,
) -> None:
    workspace_root = make_workspace(tmp_path)
    config_path = write_manager_config(workspace_root / "config.json")
    config = load_config(config_path, workspace_root=workspace_root)
    write_identity_file(config.host_repo_path)
    write_host_repo_config(config.host_repo_path, payload=host_repo_payload())

    result = RUNNER.invoke(app, ["--config", str(config_path), "select", "demo"])

    assert result.exit_code == 0, result.output
    assert "Select endpoint for 'demo':" not in result.output
    assert "Select authentication for 'demo':" not in result.output
    assert read_json(config.state_path)["selected_hosts"] == [
        {
            "server_name": "demo",
            "endpoint_name": None,
            "authentication_name": None,
        }
    ]


def test_select_fails_fast_without_prompt_when_endpoint_choice_is_ambiguous_noninteractive(
    tmp_path: Path,
) -> None:
    workspace_root = make_workspace(tmp_path)
    config_path = write_manager_config(workspace_root / "config.json")
    config = load_config(config_path, workspace_root=workspace_root)
    host_repo_path = config.host_repo_path
    write_identity_file(host_repo_path, "keys/id_home")
    write_host_repo_config(
        host_repo_path,
        payload=host_repo_payload(
            endpoints=[
                {
                    "EndPointName": "public",
                    "HostName": "public.example.com",
                    "Port": 22,
                },
                {
                    "EndPointName": "private",
                    "HostName": "private.example.com",
                    "Port": 2200,
                },
            ],
            authentications=[
                {
                    "AuthenticationName": "home",
                    "User": "fox",
                    "IdentityFile": "keys/id_home",
                }
            ],
        ),
    )

    result = RUNNER.invoke(app, ["--config", str(config_path), "select", "demo"])

    assert result.exit_code == 1
    assert "Select endpoint for 'demo':" not in result.output
    assert result.exception is not None
    assert "multiple endpoint options and interactive selection is unavailable" in str(
        result.exception
    )
    assert "--endpoint <stable_name>" in str(result.exception)
    assert "public, private" in str(result.exception)


def test_select_fails_fast_without_prompt_when_auth_choice_is_ambiguous_noninteractive(
    tmp_path: Path,
) -> None:
    workspace_root = make_workspace(tmp_path)
    config_path = write_manager_config(workspace_root / "config.json")
    config = load_config(config_path, workspace_root=workspace_root)
    host_repo_path = config.host_repo_path
    write_identity_file(host_repo_path, "keys/id_home")
    write_identity_file(host_repo_path, "keys/id_work")
    write_host_repo_config(
        host_repo_path,
        payload=host_repo_payload(
            endpoints=[{"EndPointName": "public", "HostName": "public.example.com", "Port": 22}],
            authentications=[
                {
                    "AuthenticationName": "home",
                    "User": "fox",
                    "IdentityFile": "keys/id_home",
                },
                {
                    "AuthenticationName": "work",
                    "User": "fox-work",
                    "IdentityFile": "keys/id_work",
                },
            ],
        ),
    )

    result = RUNNER.invoke(app, ["--config", str(config_path), "select", "demo"])

    assert result.exit_code == 1
    assert "Select authentication for 'demo':" not in result.output
    assert result.exception is not None
    assert "multiple authentication options and interactive selection is unavailable" in str(
        result.exception
    )
    assert "--auth <stable_name>" in str(result.exception)
    assert "home, work" in str(result.exception)


def test_select_reprompts_after_invalid_interactive_choice(
    tmp_path: Path,
    monkeypatch,
) -> None:
    workspace_root = make_workspace(tmp_path)
    config_path = write_manager_config(workspace_root / "config.json")
    config = load_config(config_path, workspace_root=workspace_root)
    host_repo_path = config.host_repo_path
    write_identity_file(host_repo_path, "keys/id_home")
    write_identity_file(host_repo_path, "keys/id_work")
    write_host_repo_config(
        host_repo_path,
        payload=host_repo_payload(
            endpoints=[
                {
                    "EndPointName": "public",
                    "HostName": "public.example.com",
                    "Port": 22,
                },
                {
                    "EndPointName": "private",
                    "HostName": "private.example.com",
                    "Port": 2200,
                },
            ],
            authentications=[
                {
                    "AuthenticationName": "home",
                    "User": "fox",
                    "IdentityFile": "keys/id_home",
                },
                {
                    "AuthenticationName": "work",
                    "User": "fox-work",
                    "IdentityFile": "keys/id_work",
                },
            ],
        ),
    )
    _force_interactive_selection(monkeypatch)

    result = RUNNER.invoke(
        app,
        ["--config", str(config_path), "select", "demo"],
        input="x\n2\n1\n",
    )

    assert result.exit_code == 0, result.output
    assert "Error: 'x' is not a valid integer range." in result.output
    assert read_json(config.state_path)["selected_hosts"] == [
        {
            "server_name": "demo",
            "endpoint_name": "private",
            "authentication_name": "home",
        }
    ]


def test_deselect_only_updates_state(tmp_path: Path) -> None:
    workspace_root = make_workspace(tmp_path)
    config_path = write_manager_config(workspace_root / "config.json")
    config = load_config(config_path, workspace_root=workspace_root)
    host_repo_path = config.host_repo_path
    write_identity_file(host_repo_path)
    write_host_repo_config(
        host_repo_path,
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

    result = RUNNER.invoke(app, ["--config", str(config_path), "deselect", "demo"])

    assert result.exit_code == 0, result.output
    assert read_json(config.state_path)["selected_hosts"] == []
    assert not config.managed_config_path.exists()


def test_select_rejects_host_without_endpoint_options(tmp_path: Path) -> None:
    workspace_root = make_workspace(tmp_path)
    config_path = write_manager_config(workspace_root / "config.json")
    config = load_config(config_path, workspace_root=workspace_root)
    write_identity_file(config.host_repo_path)
    write_host_repo_config(
        config.host_repo_path,
        payload=[
            {
                **host_shell_payload(),
                "Authentication": [
                    {
                        "AuthenticationName": "home",
                        "User": "fox",
                        "IdentityFile": "keys/id_demo",
                    }
                ],
            }
        ],
    )

    result = RUNNER.invoke(app, ["--config", str(config_path), "select", "demo", "--auth", "home"])

    assert result.exit_code == 1
    assert "Host 'demo' has no endpoint options." in str(result.exception)
    assert "repo host endpoint add demo <endpoint_name> --hostname <host>" in str(result.exception)


def test_select_rejects_host_without_authentication_options(tmp_path: Path) -> None:
    workspace_root = make_workspace(tmp_path)
    config_path = write_manager_config(workspace_root / "config.json")
    config = load_config(config_path, workspace_root=workspace_root)
    write_host_repo_config(
        config.host_repo_path,
        payload=[
            {
                **host_shell_payload(),
                "Endpoint": [{"EndPointName": "public", "HostName": "demo.example.com"}],
            }
        ],
    )

    result = RUNNER.invoke(
        app, ["--config", str(config_path), "select", "demo", "--endpoint", "public"]
    )

    assert result.exit_code == 1
    assert "Host 'demo' has no authentication options." in str(result.exception)
    assert "repo host auth add demo <auth_name>" in str(result.exception)


def test_select_rejects_host_without_endpoint_or_authentication_options(
    tmp_path: Path,
) -> None:
    workspace_root = make_workspace(tmp_path)
    config_path = write_manager_config(workspace_root / "config.json")
    config = load_config(config_path, workspace_root=workspace_root)
    write_host_repo_config(config.host_repo_path, payload=[host_shell_payload()])

    result = RUNNER.invoke(app, ["--config", str(config_path), "select", "demo"])

    assert result.exit_code == 1
    assert "Host 'demo' has no endpoint or authentication options." in str(result.exception)
    assert "repo host endpoint add demo <endpoint_name> --hostname <host>" in str(result.exception)
    assert "repo host auth add demo <auth_name>" in str(result.exception)
