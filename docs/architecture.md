# Architecture

## Layers

`keywharf` keeps the runtime split into explicit layers:

- `commands`: Typer adapters only. They parse CLI options, format terminal/JSON output, run sudo re-exec, and map failures to exit codes.
- `config`: formal manager-config schema, defaults loading, deep merge, and runtime resolution.
- `services`: workflow orchestration for `init`, `pull`, `select`, `validate`, `render`, `apply`, include installation, local views, and remote host editing.
- `storage`: JSON/file I/O, git sync, state persistence, managed-file writes, and remote repo config writes.
- `ssh_config`: low-level parse/build/render logic for managed SSH host blocks.
- `runtime`: workspace discovery and `%{DATA_ROOT}` token handling.
- `domain`: remote host models, local state models, SSH host value objects, result types, and project-specific errors.

Dependency direction stays one-way:

- `commands` -> `services`, `config`, `domain`
- `services` -> `storage`, `ssh_config`, `config`, `domain`
- `storage` -> `config`, `domain`
- `config` -> `runtime`
- `ssh_config` -> `domain`

Package `__init__.py` files stay intentionally thin and do not re-export internal implementation.

## Data Flow

Steady-state workflow:

1. `init` creates a workspace skeleton from package resources
2. `pull` clones or updates the remote repo locally
3. `remote host ...` edits the local checkout `config.json`
4. `select` / `deselect` mutate `state_path`
5. `validate` checks manager config, remote repo config, state, and include presence
6. `render` resolves state into desired `SSHHostConfig` objects and managed config text
7. `apply` copies required keys, atomically replaces `managed_config_path`, then removes stale managed keys
8. `install-include` explicitly wires the managed fragment into the main SSH config

This keeps:

- desired state separate from rendered output
- rendered output separate from filesystem mutation
- the main SSH config outside normal write paths

## Ownership Boundary

`keywharf` owns only:

- `state_path`
- `managed_config_path`
- `managed_keys_dir`

`keywharf` does not own the user's whole SSH world. Normal commands never rewrite `~/.ssh/config`; only `install-include` may append one minimal include block.

## Formal Config And Templates

Manager config follows one fixed contract:

1. load package defaults from `config_defaults/manager.json`
2. deep-merge file or mapping overrides
3. validate with Pydantic v2
4. resolve runtime paths separately

Template roles are split on purpose:

- JSON package resources provide formal defaults and starter state
- `.j2` package resources provide text scaffolding only

The managed SSH config itself remains structure-driven code, not a Jinja template.

## Privilege Model

Mutating commands share one privilege path:

1. build a canonical CLI invocation
2. re-exec through `sudo` when `--sudo` is requested
3. otherwise run a fail-fast preflight against concrete target paths
4. abort early with retry guidance when privileges are insufficient

This logic is centralized in `commands/_invocation.py`, `commands/_privilege.py`, and service-level analyzers.
