# ssh-manager

`ssh-manager` is a Python 3.11+ CLI for managing a remote SSH host/key repository without taking over your whole `~/.ssh/config`.

It manages only:

- one manager-owned SSH config fragment
- one manager-owned key directory
- one explicit local state file

The source of truth is the local state file. The managed SSH config is an `apply` artifact, not the state source.

## Workflow

Recommended flow:

```bash
ssh-manager init --data-root ~/ssh-manager
ssh-manager --config ~/ssh-manager/config.json pull
ssh-manager --config ~/ssh-manager/config.json remote list
ssh-manager --config ~/ssh-manager/config.json remote show demo
ssh-manager --config ~/ssh-manager/config.json select demo --endpoint public --auth home
ssh-manager --config ~/ssh-manager/config.json validate
ssh-manager --config ~/ssh-manager/config.json render
ssh-manager --config ~/ssh-manager/config.json apply
ssh-manager --config ~/ssh-manager/config.json install-include
```

Command model:

- `init`: create marker, config, state, and directory skeleton
- `pull`: sync the remote repo locally
- `remote list/show`: inspect remote definitions and stable selectors
- `select` / `deselect`: mutate local desired state only
- `validate`: validate config, remote schema, state, and selector stability
- `render`: print the desired managed SSH config without writing files
- `apply`: validate, render, sync keys, and atomically replace the managed config
- `local list/show`: inspect desired state versus current managed output
- `install-include`: minimally attach the managed fragment to the main SSH config

## Ownership Boundary

`ssh-manager` manages:

- `managed_config_path`
- `managed_keys_dir`
- `state_path`

`ssh-manager` does not manage:

- unrelated `Host` entries in the main SSH config
- `Match` blocks
- other `Include` directives
- user comments and ordering in the main SSH config

Only `install-include` may modify the main SSH config, and it does so by appending one minimal include block when needed.

## Manager Config

Manager config is formalized as a defaults-aware JSON config.

Defaults come from package resources:

- `pkg://ssh_manager/config_defaults/manager.json`

Load contract:

1. read package defaults
2. read file or mapping override
3. deep-merge
4. validate with Pydantic v2

The raw config stays unresolved. Runtime path expansion is separate.

Default `config.json` shape:

```json
{
  "ssh_key_remote_repo": "git@example.com:org/keys.git",
  "ssh_key_local_repo": "%{DATA_ROOT}/repos/keys",
  "ssh_dir": "~/.ssh",
  "managed_config_path": null,
  "managed_keys_dir": null,
  "state_path": "%{DATA_ROOT}/state/state.json"
}
```

Path behavior:

- `%{DATA_ROOT}` expands to the resolved data root
- `~` and environment variables are expanded at runtime
- relative paths resolve from the manager config directory
- when `managed_config_path` is `null`, it defaults to `<ssh_dir>/managed/ssh-manager.conf`
- when `managed_keys_dir` is `null`, it defaults to `<ssh_dir>/managed/keys`

## Local State

The local state file is explicit JSON:

```json
{
  "version": 1,
  "selected_hosts": [
    {
      "server_name": "demo",
      "endpoint_name": "public",
      "authentication_name": "home"
    }
  ]
}
```

Selector rules:

- one `ServerName` maps to at most one local selection entry
- `endpoint_name` may be `null` only when the remote host still has exactly one endpoint
- `authentication_name` may be `null` only when the remote host still has exactly one authentication option
- stable selection is name-based; array order is not part of the contract

## Data Root

Data root resolution uses only the final naming:

1. environment variable `SSH_MANAGER_DATA_ROOT`
2. nearest `SSH_MANAGER_DATA_ROOT` marker file from `cwd` upward
3. `SSH_MANAGER_DATA_ROOT` marker in `home`

## `init` and Package Resources

`init` does not depend on repository-root example files.

It uses package resources to create:

- manager config defaults
- empty state template

This keeps editable installs and built distributions consistent.

## `--sudo`

Mutating commands support `--sudo`:

- `init`
- `pull`
- `select`
- `deselect`
- `apply`
- `install-include`

Behavior:

- if the target paths are writable, normal user execution works without `sudo`
- if not, the command fails fast with a concrete path-based reason
- when `--sudo` is given, the full command is re-execed through `sudo`

## Installation

```bash
python3.11 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
pytest
```

Runtime requires:

- Python 3.11+
- system `git`

## Documentation

- [`docs/architecture.md`](docs/architecture.md)
- [`docs/configuration.md`](docs/configuration.md)
- [`docs/cli.md`](docs/cli.md)
- [`docs/development.md`](docs/development.md)
- [`CHANGELOG.md`](CHANGELOG.md)

