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
keywharf --workspace <path> repo host add <server>
keywharf --workspace <path> repo host endpoint add <server> <endpoint> --hostname <host>
keywharf --workspace <path> repo host auth add <server> <auth> --user <user> --identity-file keys/<id_file>
```

`keywharf init` creates `<path>/repo` as the workspace's one host repo directory. It is empty until you run `repo init`.

Then continue with the normal selection/apply flow:

```bash
keywharf --workspace <path> select <server>
# or pass stable names explicitly:
# keywharf --workspace <path> select <server> --endpoint <name> --auth <name>
keywharf --workspace <path> validate
keywharf --workspace <path> render
keywharf --workspace <path> apply
keywharf --workspace <path> install-include
```

`select` still accepts explicit `--endpoint` and `--auth` stable names. If one side has a single candidate, it is selected automatically. If one side has multiple candidates, `select` prompts in an interactive terminal and fails fast in noninteractive environments until you pass the stable name explicitly. Local state keeps name-based selectors; singleton selections may leave `endpoint_name` or `authentication_name` as `null`.

## Commands

| Command | Purpose | Writes |
| --- | --- | --- |
| `init` | create the workspace skeleton from package resources, including an empty `repo/` directory | yes |
| `repo init` | bootstrap a local-first host-repo skeleton inside `<workspace>/repo` | yes |
| `repo sync` | clone or sync the configured host repo into `<workspace>/repo` | yes |
| `repo host list/show` | inspect host shells in the host repo | no |
| `repo host add/update/remove` | edit host-level fields only | yes |
| `repo host endpoint list/show` | inspect named endpoint options for one host | no |
| `repo host endpoint add/update/remove` | edit endpoint options only | yes |
| `repo host auth list/show` | inspect named authentication options for one host | no |
| `repo host auth add/update/remove` | edit authentication options only | yes |
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
- `repo host endpoint list`
- `repo host endpoint show`
- `repo host endpoint add`
- `repo host endpoint update`
- `repo host endpoint remove`
- `repo host auth list`
- `repo host auth show`
- `repo host auth add`
- `repo host auth update`
- `repo host auth remove`
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
- `repo host endpoint add`
- `repo host endpoint update`
- `repo host endpoint remove`
- `repo host auth add`
- `repo host auth update`
- `repo host auth remove`

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
- `repo host add` creates a host shell only; add endpoint/auth options separately before selecting it
- `validate` reports every incomplete host shell in the repo at once
- `render` and `apply` require only selected hosts to be complete
- `repo init` never runs `git init`, creates `.git`, runs `git remote add`, `commit`, or `push`
- if you want `<workspace>/repo` to become a real git repository, do that yourself after `repo init`
- normal commands do not rewrite the main SSH config
