# Architecture

## Layers

`ssh-manager` is organized into explicit layers:

- `commands`: Typer CLI adapters. They parse flags, map errors to exit codes, and format human/JSON output.
- `services`: application logic for `init`, `pull`, `select/deselect`, `validate`, `render`, `apply`, local status views, and include installation.
- `domain`: shared models and result objects such as `ManagerConfig`, local state models, render/apply results, and SSH host value objects.
- `storage`: JSON/state I/O, git sync, manager-owned SSH config/key file writes, include detection/installation helpers, and atomic writes.
- `ssh_config`: low-level parse/build/render logic for managed SSH host blocks.
- `runtime`: data-root discovery, config loading, default config payload assembly, and path expansion.

## Dependency Direction

Preferred dependency direction is:

- `commands` -> `services`, `runtime`, `domain`
- `services` -> `storage`, `ssh_config`, `domain`
- `storage` -> `domain`
- `runtime` -> `storage`, `domain`
- `ssh_config` -> `domain`
- `domain` -> no project-internal layer

Avoid reverse dependencies. In particular:

- `services` must not depend on `commands`
- `storage` and `domain` must stay CLI-agnostic
- CLI adapters should not implement business rules or file mutation logic

## State and Apply Flow

Stage three changes the core flow from “managed config as state” to “explicit desired state plus apply”.

The intended flow is:

1. `init` creates a data root, config template, and empty state file.
2. `select` / `deselect` mutate `state_path` only.
3. `validate` checks manager config, remote repo schema, local state, selector stability, and warnings such as missing include/orphaned managed hosts.
4. `render` resolves state against the remote repo and produces a structured preview:
   - desired `SSHHostConfig` objects
   - managed config text
   - planned key copies
   - planned stale-key deletions
5. `apply` runs validation, renders the desired output, syncs manager-owned keys, atomically replaces `managed_config_path`, and only then removes stale managed keys.

This keeps “selection state” and “materialized files” separate.

## Ownership Boundary

The stage-two ownership boundary remains in force:

- ssh-manager owns `managed_config_path`
- ssh-manager owns `managed_keys_dir`
- ssh-manager owns `state_path`
- ssh-manager does not own the full main SSH config
- `install-include` is the only explicit path that may minimally modify `<ssh_dir>/config`

Operational consequences:

- `local list/show` inspect local state and current managed output, not the whole user SSH world
- `render` and `apply` operate only on manager-owned files
- unrelated user `Host`, `Match`, `Include`, comments, and ordering remain untouched

## Responsibility Boundaries

- CLI override handling, config-path resolution, and user-facing error translation happen at the CLI/runtime boundary.
- Services receive resolved `ManagerConfig` objects. They should not be asked to expand `~`, `%{DATA_ROOT}`, or relative paths.
- The local desired state file is loaded/saved only through storage helpers, not directly from CLI code.
- SSH text rendering/parsing belongs to `ssh_config`, not to commands or storage.
- The legacy `SSHManager` class remains only as a thin compatibility facade over managed-output behavior. It is not the source of truth for desired state.

## Current Phase Boundaries

This phase intentionally does not do the following:

- redesign the remote repo schema
- support multiple selected variants for one `ServerName`
- auto-import old stage-two managed config into local state
- change the stage-two include ownership model
- rename the package, distribution, or CLI
