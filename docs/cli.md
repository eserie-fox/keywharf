# CLI

## Recommended Workflow

1. `ssh-manager init --data-root <path>`
2. `ssh-manager --config <path>/config.json pull`
3. `ssh-manager --config <path>/config.json remote list`
4. `ssh-manager --config <path>/config.json remote show <server>`
5. `ssh-manager --config <path>/config.json select <server> --endpoint <name> --auth <name>`
6. `ssh-manager --config <path>/config.json validate`
7. `ssh-manager --config <path>/config.json render`
8. `ssh-manager --config <path>/config.json apply`
9. `ssh-manager --config <path>/config.json install-include`

## Primary Commands

- `init`: create marker/config/state skeleton; no repo sync, no include installation, no managed-config write
- `pull`: clone or sync the remote repo
- `remote list/show`: inspect remote hosts and stable selector names
- `select`: upsert one desired selection into local state
- `deselect`: remove one desired selection from local state
- `validate`: validate config, remote schema, state selectors, and warnings
- `render`: print the desired managed SSH config preview; no file writes
- `apply`: validate, render, sync managed keys, and atomically replace the managed config
- `local list/show`: inspect desired state versus current managed output
- `install-include`: install or preview a minimal OpenSSH include line

## Compatibility Aliases

These remain available, but the new command model is preferred:

- `add`: compatibility alias for `select`
- `remove`: compatibility alias for `deselect`
- `check`: compatibility alias for `validate`
- `flush`: compatibility alias for `apply`

Alias semantics are intentionally conservative:

- `add` updates local state only; it no longer writes the managed config directly
- `remove` updates local state only
- `flush --dry-run` is effectively a preview of `apply`
- compatibility command help/output explicitly points users to the new commands

## JSON Output

Commands with structured `--json` output:

- `validate`
- `render`
- `apply`
- `local list`
- `local show`
- `remote list`
- `remote show`

Text mode is optimized for operators. JSON mode is intended for scripting.

## Exit Codes

- `0`: success
- `1`: validation failure or operation failure
- `2`: CLI/config assembly error, such as invalid parameters or missing manager config

## Safety Notes

- `render` never writes files
- `apply --dry-run` never writes files
- `apply` fails by default when local state is empty but the current managed config still contains hosts
- use `apply --allow-empty` only when you intentionally want to clear an existing managed config
