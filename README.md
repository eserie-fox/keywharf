# keywharf

`keywharf` is a Python 3.11+ CLI for selecting SSH host definitions from a host repo into a local desired state, then materializing only manager-owned SSH artifacts.

It manages only:

- one explicit local state file
- one managed SSH config fragment
- one managed key directory

It does not take over the user's whole `~/.ssh/config`. Only `install-include` may minimally append one `Include` block to the main SSH config.

## Recommended Workflow

Create one named workspace:

```bash
keywharf init demo --directory ~
```

If you already have a host repo remote URL:

```bash
# edit ~/demo/config.json and set host_repo_remote_url
keywharf --workspace ~/demo repo sync
keywharf --workspace ~/demo repo host list
keywharf --workspace ~/demo repo host show demo
```

If you are starting from scratch:

```bash
keywharf --workspace ~/demo repo init
keywharf --workspace ~/demo repo host add demo --hostname demo.example.com --user fox --identity-file keys/id_demo
```

`keywharf init` creates `~/demo/repo` as the workspace's one host repo directory, but it starts empty. `repo init` writes the host repo skeleton there. If you want it to become a real git repository, run `git init`, `git remote add`, and `git push` in `~/demo/repo` yourself.

Then continue with normal selection and apply flow:

```bash
keywharf --workspace ~/demo select demo --endpoint public --auth home
keywharf --workspace ~/demo validate
keywharf --workspace ~/demo render
keywharf --workspace ~/demo apply
keywharf --workspace ~/demo install-include
```

If the manager config lives outside the default workspace root, use `--config <path>` instead of `--workspace`.

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

1. `--workspace`
2. `KEYWHARF_WORKSPACE`
3. auto-search `pwd`, each ancestor, then `~`
4. for each base directory: scan one level of child directories first, then the base directory itself
5. the first directory containing `KEYWHARF_WORKSPACE` wins
6. fail fast with the checked candidate paths listed

`keywharf init <workspace_name>` creates the marker, `config.json`, `state/state.json`, an empty `repo/` directory, and small workspace text files from package resources. It does not touch `~/.ssh` and does not initialize a git repo for you.

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

## Host Repo CRUD

`repo init` bootstraps a local-first host repo skeleton:

- empty `config.json`
- `keys/`
- `.gitignore`

It writes those files into the workspace's one host repo directory, `%{WORKSPACE}/repo`. It does not run `git init` or create `.git`.

`repo host` edits only the host repo `config.json`:

- `repo host list`
- `repo host show`
- `repo host add`
- `repo host update`
- `repo host remove`

These commands do not commit, push, run `git init`, or mutate git metadata. They perform structured JSON reads/writes, preserve array order, and revalidate the resulting host set before writing.

This round only adds Host-level CRUD. `ExtraConfig` is preserved and rendered, but it is not exposed as a CLI editor yet.

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
