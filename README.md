# ssh-manager

`ssh-manager` is a Python 3.11+ CLI for managing a local `~/.ssh/config` from a remote SSH key/config repository. It keeps the existing command model in place for this phase: `pull`, `local`, `remote`, `add`, `remove`, `flush`, and `check`.

This repository has been refactored into a standard `src/` layout with explicit `commands`, `services`, `domain`, `storage`, `ssh_config`, and `runtime` layers. This phase is a foundation cleanup only. It does not introduce managed include files or redesign the command semantics.

## Highlights

- Standard `src/ssh_manager/` package layout.
- Thin CLI adapter layer built on Typer.
- Service-layer orchestration for `pull`, `add/remove`, `flush`, and `check`.
- Explicit runtime config and data-root resolution.
- Pure validation for `check`: it no longer rewrites remote `config.json`.

## Installation

Install from a local checkout:

```bash
python3.11 -m venv .venv
. .venv/bin/activate
python -m pip install .
ssh-manager --help
```

For development:

```bash
python3.11 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
pytest
```

## Data Root

`ssh-manager` resolves its data root in this order:

1. `SSH_MANAGER_DATA_ROOT`
2. the nearest `SSH_MANAGER_DATA_ROOT` marker file found in the working directory, its parents, or a direct child of those directories
3. legacy alias `SSH_CONFIG_DATA_ROOT`
4. legacy marker `SSH_CONFIG_DATA_ROOT`

Create a data root with the current marker:

```bash
mkdir -p ~/ssh-manager-data
touch ~/ssh-manager-data/SSH_MANAGER_DATA_ROOT
```

Legacy `SSH_CONFIG_DATA_ROOT` naming is still accepted for compatibility, but documentation and error messages now use `SSH_MANAGER_DATA_ROOT` as the canonical name.

## Manager Config

Place `config.json` under the resolved data root, or pass `--config`.

Example:

```json
{
  "ssh_key_remote_repo": "git@your.git.server:org/keys.git",
  "ssh_key_local_repo": "%{DATA_ROOT}/repos/keys",
  "ssh_dir": "~/.ssh"
}
```

Path fields support:

- `~`
- environment variables such as `$HOME`
- `%{DATA_ROOT}`
- relative paths, resolved from the manager config file directory

The remote key repo still expects a `config.json` shaped like [`config_example/ssh_key_repo_example_config.json`](config_example/ssh_key_repo_example_config.json).

## Commands

- `ssh-manager pull`: clone or sync the remote repo into the configured local repo path
- `ssh-manager local list`: inspect local `~/.ssh/config` host blocks
- `ssh-manager remote list`: inspect remote host definitions
- `ssh-manager remote show <name>`: inspect one remote host definition
- `ssh-manager add <name>`: generate and add a host block locally
- `ssh-manager remove <name|index>`: remove a local host block and its copied identity file
- `ssh-manager flush`: rewrite the local SSH config from the current parsed host set
- `ssh-manager check`: validate the remote repo config without modifying files

Mutating commands still rewrite a single SSH config file and keep timestamped backups where applicable. This phase intentionally does not add include-file management.

## `check` Behavior

`check` is now validation-only:

- it loads the remote repo `config.json`
- it verifies required server names
- it verifies referenced `IdentityFile` paths exist inside the local repo checkout
- it does not sort, rewrite, or back up `config.json`

## Documentation

- [`docs/architecture.md`](docs/architecture.md): codebase layers and dependency direction
- [`docs/configuration.md`](docs/configuration.md): manager config, remote repo config, and data-root resolution
- [`docs/development.md`](docs/development.md): local setup, tests, packaging, and repository hygiene
- [`CHANGELOG.md`](CHANGELOG.md): release history

## Development Notes

- Source code lives under `src/ssh_manager/`
- Tests live under `tests/`
- Run the CLI from source with `PYTHONPATH=src python -m ssh_manager --help`
- This phase keeps package name `ssh_manager`, distribution name `ssh-manager`, and CLI name `ssh-manager` unchanged
