# CLI

## Recommended Workflow

```bash
ssh-manager init --data-root <path>
ssh-manager --config <path>/config.json pull
ssh-manager --config <path>/config.json remote list
ssh-manager --config <path>/config.json remote show <server>
ssh-manager --config <path>/config.json select <server> --endpoint <name> --auth <name>
ssh-manager --config <path>/config.json validate
ssh-manager --config <path>/config.json render
ssh-manager --config <path>/config.json apply
ssh-manager --config <path>/config.json install-include
```

## Commands

| Command | Purpose | Writes |
| --- | --- | --- |
| `init` | create data-root skeleton from package resources | yes |
| `pull` | clone or update the remote repo | yes |
| `remote list/show` | inspect remote hosts and stable selectors | no |
| `select` | upsert one desired selection into state | yes |
| `deselect` | remove one desired selection from state | yes |
| `validate` | validate config, remote repo, state, and warnings | no |
| `render` | preview desired managed SSH config | no |
| `apply` | validate, render, copy keys, replace managed config | yes |
| `local list/show` | inspect state versus current managed output | no |
| `install-include` | install or preview Include in main SSH config | yes |

## JSON Output

Structured `--json` output is available on:

- `validate`
- `render`
- `apply`
- `remote list`
- `remote show`
- `local list`
- `local show`

## Exit Codes

- `0`: success
- `1`: validation failure or operation failure
- `2`: CLI or config assembly error

## `--sudo`

Mutating commands support `--sudo`:

- `init`
- `pull`
- `select`
- `deselect`
- `apply`
- `install-include`

Behavior:

- when not needed, normal user execution works as-is
- when needed, commands fail fast with explicit path-based reasons
- with `--sudo`, the full command is re-execed through `sudo`

## Safety Notes

- `render` never writes files
- `apply --dry-run` never writes files
- `install-include --dry-run` never writes files
- `apply` refuses to clear a non-empty managed config when state is empty unless `--allow-empty` is set
- normal commands do not rewrite the main SSH config

