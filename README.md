# keywharf

`keywharf` is a Python 3.11+ CLI for selecting remote SSH host definitions into a local desired state, then materializing only manager-owned SSH artifacts.

It manages only:

- one explicit local state file
- one managed SSH config fragment
- one managed key directory

It does not take over the user's whole `~/.ssh/config`. Only `install-include` may minimally append one `Include` block to the main SSH config.

## Recommended Workflow

```bash
keywharf --data-root ~/keywharf init
keywharf --data-root ~/keywharf pull
keywharf --data-root ~/keywharf remote host list
keywharf --data-root ~/keywharf remote host show demo
keywharf --data-root ~/keywharf remote host add demo --hostname demo.example.com --user fox --identity-file keys/id_demo
keywharf --data-root ~/keywharf select demo --endpoint public --auth home
keywharf --data-root ~/keywharf validate
keywharf --data-root ~/keywharf render
keywharf --data-root ~/keywharf apply
keywharf --data-root ~/keywharf install-include
```

If the manager config lives outside the default workspace root, use `--config <path>` instead of `--data-root`.

## Ownership Boundary

`keywharf` manages:

- `state_path`
- `managed_config_path`
- `managed_keys_dir`

`keywharf` does not manage:

- unrelated `Host` entries in the main SSH config
- `Match` blocks
- other `Include` lines
- user comments and ordering in the main SSH config

## Workspace Discovery

Workspace resolution is explicit and predictable:

1. `--data-root`
2. `KEYWHARF_DATA_ROOT`
3. current directory, if it already contains both the `KEYWHARF_DATA_ROOT` marker and `config.json`
4. nearest ancestor workspace marker
5. `~/keywharf`
6. fail with the checked candidate paths listed

`keywharf init` creates the marker, `config.json`, `state/state.json`, directory skeleton, and small workspace text files from package resources.

## Formal Config And Templates

Manager config is a formal runtime config:

- defaults come from `pkg://keywharf/config_defaults/manager.json`
- file or mapping input is override only
- defaults and overrides are deep-merged before Pydantic v2 validation
- runtime path resolution is separate from raw config loading

Resource roles are intentionally split:

- `config_defaults/*.json`: formal defaults for manager config
- `templates/*.json`: structured starter data such as the empty state file
- `templates/*.j2`: human-facing text templates such as workspace `README.md`, workspace `.gitignore`, and the include block text

## Remote Host CRUD

`remote host` edits only the local checkout copy of the remote repository config:

- `remote host list`
- `remote host show`
- `remote host add`
- `remote host update`
- `remote host remove`

These commands do not commit, push, or mutate git metadata. They perform structured JSON reads/writes, preserve array order, and revalidate the resulting host set before writing.

This round only adds Host-level CRUD. `ExtraConfig` is preserved and rendered, but it is not exposed as a CLI editor yet.

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

Privilege handling is centralized:

- normal writable paths run without sudo
- unwritable paths fail fast with concrete path-based reasons
- `--sudo` re-execs the full command through `sudo`

## Installation

```bash
python3.11 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
pytest
```

Runtime requirements:

- Python 3.11+
- system `git`

## Documentation

- [`docs/architecture.md`](docs/architecture.md)
- [`docs/configuration.md`](docs/configuration.md)
- [`docs/cli.md`](docs/cli.md)
- [`docs/development.md`](docs/development.md)
- [`CHANGELOG.md`](CHANGELOG.md)
