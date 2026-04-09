# Architecture

## Layers

`ssh-manager` is organized into explicit layers:

- `commands`: Typer adapters. They parse CLI flags, format terminal/JSON output, run privilege re-exec, and translate errors into exit behavior.
- `config`: formal manager-config schema, package defaults loading, deep merge, and runtime resolution.
- `services`: application logic for `init`, `pull`, `select`, `deselect`, `validate`, `render`, `apply`, local views, and include installation.
- `storage`: JSON/file I/O, git sync, manager-owned SSH file writes, include detection, and state persistence.
- `ssh_config`: low-level parse/build/render logic for managed SSH host blocks.
- `runtime`: data-root discovery and `%{DATA_ROOT}` token handling.
- `domain`: state models, remote host models, SSH host value objects, result objects, and project-specific errors.

## Dependency Direction

Preferred direction:

- `commands` -> `services`, `config`, `domain`
- `services` -> `storage`, `ssh_config`, `config`, `domain`
- `storage` -> `domain`, `config`
- `config` -> `runtime`
- `ssh_config` -> `domain`
- `runtime` -> no heavier internal layer
- `domain` -> no project-internal layer

Avoid reverse dependencies. In particular:

- `services` must not depend on CLI modules
- `storage` must stay CLI-agnostic
- `config` must not depend on services
- package `__init__.py` files stay thin and do not pull heavy runtime dependencies

## Data Flow

The steady-state workflow is:

1. `init` creates data-root skeleton from package resources
2. `pull` syncs the remote repo locally
3. `select` / `deselect` mutate `state_path`
4. `validate` checks manager config, remote repo schema, state, and include presence
5. `render` resolves state into desired `SSHHostConfig` objects and managed config text
6. `apply` copies required keys, atomically replaces `managed_config_path`, then removes stale keys
7. `install-include` explicitly connects the managed fragment to the main SSH config

This keeps:

- desired state separate from rendered output
- rendered output separate from file materialization
- main SSH config outside the normal write path

## Ownership Boundary

`ssh-manager` owns only:

- `managed_config_path`
- `managed_keys_dir`
- `state_path`

`ssh-manager` does not own the user's broader SSH config world.

Normal commands do not rewrite the main SSH config. Only `install-include` may minimally append one include block.

## Formal Config

Manager config follows one fixed contract:

1. load package defaults from `config_defaults/manager.json`
2. deep-merge file or mapping override
3. validate with Pydantic v2
4. resolve runtime paths separately

Raw config remains declarative. Runtime expansion of `~`, env vars, `%{DATA_ROOT}`, and relative paths happens only in the resolver.

## Privilege Model

Mutating commands share one privilege flow:

1. build canonical CLI invocation
2. if `--sudo` is present, re-exec the full command through `sudo`
3. otherwise run a fail-fast preflight against the concrete target paths
4. abort early with retry guidance when privileges are insufficient

This logic is centralized in `commands/_invocation.py`, `commands/_privilege.py`, and service-level privilege analyzers.

