# Architecture

## Layers

`ssh-manager` is now organized into explicit layers:

- `commands`: Typer command registration, argument parsing, Rich/JSON output, and exit behavior
- `services`: application logic for `pull`, `check`, local host loading, remote host loading, and add/remove/flush orchestration
- `domain`: shared models and result objects
- `storage`: JSON file I/O, git repo sync, local SSH config file writes, backups, and identity file copy/delete
- `ssh_config`: low-level parse/build/render logic for SSH host blocks
- `runtime`: data-root discovery, config loading, path expansion, and optional runtime logging helpers

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
- CLI adapters should not directly implement business rules or file mutation logic

## Responsibility Boundaries

- CLI override handling, config-path resolution, and user-facing error translation happen at the CLI/runtime boundary.
- Services receive already-resolved `ManagerConfig` objects.
- `check` belongs to the service layer and is pure validation in this phase.
- SSH rendering and parsing belong to `ssh_config`, not the CLI and not the storage layer.
- The legacy `SSHManager` class remains only as a thin compatibility facade over the service layer.

## Current Phase Boundaries

This refactor intentionally does not do the following:

- managed include file mode
- command model redesign
- package/distribution/CLI rename
- remote repo schema redesign

The local write model remains a single managed SSH config file with timestamped backups for mutating writes.
