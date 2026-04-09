# ssh-manager

`ssh-manager` is a Python 3.11+ CLI for managing SSH host entries from a remote SSH key/config repository. It no longer takes ownership of the whole `~/.ssh/config`. It manages only its own config fragment and managed key copies, and in this phase it also uses an explicit local state file so “which hosts are selected” is separate from “what has been applied”.

## Highlights

- Standard `src/ssh_manager/` layout with explicit `commands`, `services`, `domain`, `storage`, `ssh_config`, and `runtime` layers.
- Recommended workflow: `init -> pull -> remote -> select -> validate -> render -> apply`.
- Explicit local desired state at `state_path`; `managed_config_path` is now an apply artifact, not the source of truth.
- Clear ownership boundary: only manager-owned config/key files are managed; the main SSH config is touched only by `install-include`.
- Compatibility aliases remain for `add/remove/flush/check`, but the new command model is the primary interface.

## Installation

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
2. the nearest `SSH_MANAGER_DATA_ROOT` marker file
3. legacy alias `SSH_CONFIG_DATA_ROOT`
4. legacy marker `SSH_CONFIG_DATA_ROOT`

Canonical naming is now `SSH_MANAGER_DATA_ROOT`. Legacy names are still accepted for compatibility.

## Recommended Workflow

Initialize a minimal workspace skeleton:

```bash
ssh-manager init --data-root ~/ssh-manager-data
```

This creates:

- `SSH_MANAGER_DATA_ROOT` marker
- `config.json` template
- empty `state/state.json`

Then:

```bash
ssh-manager --config ~/ssh-manager-data/config.json pull
ssh-manager --config ~/ssh-manager-data/config.json remote list
ssh-manager --config ~/ssh-manager-data/config.json remote show demo
ssh-manager --config ~/ssh-manager-data/config.json select demo --endpoint public --auth home
ssh-manager --config ~/ssh-manager-data/config.json validate
ssh-manager --config ~/ssh-manager-data/config.json render
ssh-manager --config ~/ssh-manager-data/config.json apply
ssh-manager --config ~/ssh-manager-data/config.json install-include
```

`render` previews the desired managed SSH config without writing files. `apply` performs validation, key material sync, and atomic replacement of the managed config fragment.

## Manager Config

Manager config lives at `<data-root>/config.json` by default.

Example:

```json
{
  "ssh_key_remote_repo": "git@your.git.server:org/keys.git",
  "ssh_key_local_repo": "%{DATA_ROOT}/repos/keys",
  "ssh_dir": "~/.ssh",
  "managed_config_path": "~/.ssh/managed/ssh-manager.conf",
  "managed_keys_dir": "~/.ssh/managed/keys",
  "state_path": "%{DATA_ROOT}/state/state.json"
}
```

Path fields support:

- `~`
- environment variables
- `%{DATA_ROOT}`
- relative paths resolved from the manager config directory

Defaults when omitted:

- `main_config_path = <ssh_dir>/config`
- `managed_config_path = <ssh_dir>/managed/ssh-manager.conf`
- `managed_keys_dir = <ssh_dir>/managed/keys`
- `state_path = <data_root>/state/state.json`

## Local State Model

The local state file is the desired source of truth:

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

Rules:

- one `ServerName` maps to at most one selected entry
- `endpoint_name` / `authentication_name` may be `null` only when the remote host still has exactly one endpoint/authentication option
- once the remote repo grows from one option to multiple options, old `null` selectors become invalid and must be re-selected explicitly

## Ownership Boundary

`ssh-manager` manages:

- `managed_config_path`
- `managed_keys_dir`
- `state_path`
- the main SSH config only when you explicitly run `ssh-manager install-include`

`ssh-manager` does not manage:

- unrelated user `Host` entries
- `Match` blocks
- other `Include` lines
- user comments and ordering in the main config

## Connecting the Managed Config

Recommended:

```bash
ssh-manager install-include
```

Manual alternative:

```sshconfig
Include ~/.ssh/managed/ssh-manager.conf
```

Only `install-include` may modify the main SSH config, and even then it only appends a minimal include block when needed.

## Command Model

Primary commands:

- `init`: create marker/config/state skeleton
- `pull`: sync the remote repo
- `remote list/show`: inspect remote hosts and stable selectors
- `select` / `deselect`: mutate local desired state only
- `validate`: validate manager config, remote repo config, local state, selector stability, and warnings
- `render`: preview the desired managed config and key plan without writing files
- `apply`: validate, render, sync keys, and atomically replace the managed config
- `local list/show`: inspect local state, desired output, current managed output, and `applied/pending/invalid/orphaned` status
- `install-include`: attach the managed fragment to OpenSSH

Compatibility aliases remain:

- `add -> select`
- `remove -> deselect`
- `check -> validate`
- `flush -> apply`

These aliases are intentionally transitional. The recommended user model is now `select/render/apply`, not `add/remove/flush`.

## Migration Notes

### From pre-stage-two whole-main-config ownership

There is still no automatic migration from older versions that rewrote the whole `~/.ssh/config`. Move the ssh-manager-managed fragment into `managed_config_path`, then install the include.

### From stage-two managed-config-as-state

There is no automatic import from stage-two `managed_config_path` into the new explicit local state. Recreate selections manually with `select` before using `apply`.

`apply` now has a guard: if local state is empty but `managed_config_path` still contains hosts, it fails unless you explicitly pass `--allow-empty`.

## Documentation

- [`docs/architecture.md`](docs/architecture.md): layer boundaries and state/render/apply flow
- [`docs/configuration.md`](docs/configuration.md): manager config, state schema, selector rules, and safety guards
- [`docs/cli.md`](docs/cli.md): command matrix, compatibility aliases, and example workflows
- [`docs/development.md`](docs/development.md): local development and test coverage
- [`CHANGELOG.md`](CHANGELOG.md): release history

## Development Notes

- Source code lives under `src/ssh_manager/`
- Tests live under `tests/`
- Run from source with `PYTHONPATH=src python -m ssh_manager --help`
- Package name `ssh_manager`, distribution name `ssh-manager`, and CLI name `ssh-manager` remain unchanged
