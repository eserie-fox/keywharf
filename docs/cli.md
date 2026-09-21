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

High-frequency read-only convenience views are also available:

```bash
keywharf --workspace <path> list repo
keywharf --workspace <path> show repo <server>
keywharf --workspace <path> list local
keywharf --workspace <path> show local <server>
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
| `list repo`, `show repo <server>` | convenience read-only facade for `repo host list/show`; here `repo` means host definitions | no |
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
| `list local`, `show local <server>` | convenience read-only facade for `local list/show` | no |
| `install-include` | install or preview the `Include` line in the main SSH config | yes |

Canonical paths remain primary:

- `repo host list` and `repo host show <server>`
- `local list` and `local show <server>`

Convenience boundary:

- facade targets are only `repo` and `local`
- no `list/show` convenience facade for `endpoint` or `auth`
- no convenience facade for add/update/remove/edit operations

## JSON Output

Structured `--json` output is available on:

- `validate`
- `render`
- `apply`
- `repo host list`
- `repo host show`
- `list repo`
- `show repo`
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
- `list local`
- `show local`

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
- `repo sync` requires the configured URL to equal `origin`, uses a fast-forward-only pull, and never commits, pushes,
  resets, stashes, cleans, or changes remotes
- GitPython drives the required system Git executable, so system credential helpers and SSH settings still apply
- normal commands do not rewrite the main SSH config

## Selecting SSH Names and Editing Aliases

```bash
keywharf repo host add demo-node-01 --alias dev --alias work
# Add endpoint/authentication options separately; aliases do not complete a host shell.
keywharf select demo-node-01 --endpoint direct --auth developer --name demo-node-01 --name dev
keywharf select demo-node-01 --endpoint direct --auth developer --name dev
keywharf repo host update demo-node-01 --alias dev
keywharf repo host update demo-node-01 --clear-aliases
```

Repeated `--name` **replaces** the enabled set. Duplicate, malformed, or undeclared names fail
before saving. Without `--name`, noninteractive first selection enables only `ServerName`, and
reselection preserves the enabled set, including when endpoint/authentication choices change.
In a terminal, multiple available names produce a numbered multi-selection prompt accepting
comma-separated numbers. Enter accepts the canonical-only or previous selection default. Explicit
names or a single available name suppress this prompt. Cancellation/EOF leaves state unchanged.
A stale enabled name requires explicit `--name` replacement, even in an interactive terminal.
Endpoint/authentication singleton and noninteractive ambiguity rules remain unchanged.

On host add, omitted `--alias` means no aliases. On update, omission preserves aliases, repeated
`--alias` replaces them, and `--clear-aliases` empties them. Replacement and clearing conflict.
Failed edits leave the file unchanged. Edits preserve unrelated fields and array order; they do
not alter local state or run `apply`. Removal/rename warnings identify affected local selections.
All management selectors take canonical `ServerName`; aliases are never resolved as identifiers.

Repo JSON includes `Aliases` when non-empty. Local `selection` JSON includes `host_names`.
Rendered/current/desired SSH objects now use `server_name` and `host_names` instead of the old
single `name` field. Human repo views show available aliases; local views show enabled names.
The read-only convenience facades return the same shapes as their canonical commands. Repeated
`--name` and `--alias` survive sudo reconstruction as separate options.

See [configuration](configuration.md#state-upgrade-and-coordinated-rollout) for v1 conversion,
state-write timing, rename consequences, and software-first rollout/downgrade limitations.
