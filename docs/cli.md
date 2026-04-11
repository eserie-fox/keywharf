# CLI

## Root Options

- `--config <path>`: explicit manager config file
- `--workspace <path>`: explicit workspace root
- `--version`

Use `--workspace` for the normal workspace layout. Use `--config` when the config file lives in a custom location under that workspace.

## Recommended Workflow

Create one named workspace:

```bash
keywharf init <workspace_name> [--directory <base_dir>]
```

If you already have a host repo remote URL:

```bash
# edit <path>/config.json and set host_repo_remote_url
keywharf --workspace <path> repo sync
keywharf --workspace <path> repo host list
```

If you are starting from scratch:

```bash
keywharf --workspace <path> repo init
keywharf --workspace <path> repo host add <server> --hostname <host> --user <user> --identity-file keys/<id_file>
```

`keywharf init` creates `<path>/repo` as the workspace's one host repo directory. It is empty until you run `repo init`.

Then continue with the normal selection/apply flow:

```bash
keywharf --workspace <path> select <server> --endpoint <name> --auth <name>
keywharf --workspace <path> validate
keywharf --workspace <path> render
keywharf --workspace <path> apply
keywharf --workspace <path> install-include
```

## Commands

| Command | Purpose | Writes |
| --- | --- | --- |
| `init` | create the workspace skeleton from package resources, including an empty `repo/` directory | yes |
| `repo init` | bootstrap a local-first host-repo skeleton inside `<workspace>/repo` | yes |
| `repo sync` | clone or sync the configured host repo into `<workspace>/repo` | yes |
| `repo host list/show` | inspect host definitions in the host repo | no |
| `repo host add/update/remove` | structure-edit the host repo `config.json` | yes |
| `select` | upsert one desired selection from the host repo into state | yes |
| `deselect` | remove one desired selection from state | yes |
| `validate` | validate config, host repo, state, and include warnings | no |
| `render` | preview the desired managed SSH config | no |
| `apply` | validate, render, copy keys, replace managed config | yes |
| `local list/show` | inspect state versus current managed output | no |
| `install-include` | install or preview the `Include` line in the main SSH config | yes |

## JSON Output

Structured `--json` output is available on:

- `validate`
- `render`
- `apply`
- `repo host list`
- `repo host show`
- `repo host add`
- `repo host update`
- `repo host remove`
- `local list`
- `local show`

## Exit Codes

- `0`: success
- `1`: validation failure or operation failure
- `2`: CLI or config assembly error

## `--sudo`

Mutating commands support `--sudo`:

- `init`
- `repo init`
- `repo sync`
- `select`
- `deselect`
- `apply`
- `install-include`
- `repo host add`
- `repo host update`
- `repo host remove`

Behavior:

- writable paths run normally without sudo
- unwritable paths fail fast with explicit path-based reasons
- `--sudo` re-execs the full command through `sudo`

## Safety Notes

- `render` never writes files
- `apply --dry-run` never writes files
- `install-include --dry-run` never writes files
- `apply` refuses to clear a non-empty managed config when state is empty unless `--allow-empty` is set
- `repo host ...` edits only the host repo config and never auto-pushes git changes
- `repo init` never runs `git init`, creates `.git`, runs `git remote add`, `commit`, or `push`
- if you want `<workspace>/repo` to become a real git repository, do that yourself after `repo init`
- normal commands do not rewrite the main SSH config
