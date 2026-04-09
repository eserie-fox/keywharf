# CLI

## Root Options

- `--config <path>`: explicit manager config file
- `--data-root <path>`: explicit workspace root
- `--version`

Use `--data-root` for the normal workspace layout. Use `--config` when the config file lives in a custom location under that workspace.

## Recommended Workflow

```bash
keywharf --data-root <path> init
keywharf --data-root <path> pull
keywharf --data-root <path> remote host list
keywharf --data-root <path> remote host show <server>
keywharf --data-root <path> remote host add <server> --hostname <host> --user <user> --identity-file <path>
keywharf --data-root <path> select <server> --endpoint <name> --auth <name>
keywharf --data-root <path> validate
keywharf --data-root <path> render
keywharf --data-root <path> apply
keywharf --data-root <path> install-include
```

## Commands

| Command | Purpose | Writes |
| --- | --- | --- |
| `init` | create the workspace skeleton from package resources | yes |
| `pull` | clone or update the remote repo checkout | yes |
| `remote host list/show` | inspect local checkout host definitions | no |
| `remote host add/update/remove` | structure-edit the local checkout `config.json` | yes |
| `select` | upsert one desired selection into state | yes |
| `deselect` | remove one desired selection from state | yes |
| `validate` | validate config, remote repo, state, and include warnings | no |
| `render` | preview the desired managed SSH config | no |
| `apply` | validate, render, copy keys, replace managed config | yes |
| `local list/show` | inspect state versus current managed output | no |
| `install-include` | install or preview the `Include` line in the main SSH config | yes |

## JSON Output

Structured `--json` output is available on:

- `validate`
- `render`
- `apply`
- `remote host list`
- `remote host show`
- `remote host add`
- `remote host update`
- `remote host remove`
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
- `remote host add`
- `remote host update`
- `remote host remove`

Behavior:

- writable paths run normally without sudo
- unwritable paths fail fast with explicit path-based reasons
- `--sudo` re-execs the full command through `sudo`

## Safety Notes

- `render` never writes files
- `apply --dry-run` never writes files
- `install-include --dry-run` never writes files
- `apply` refuses to clear a non-empty managed config when state is empty unless `--allow-empty` is set
- `remote host ...` edits only the local checkout config and never auto-pushes git changes
- normal commands do not rewrite the main SSH config
