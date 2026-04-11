# Development

## Prerequisites

- Python 3.11+
- system `git`

Typical setup:

```bash
python3.11 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
```

## Repository Layout

- `src/keywharf/`: package source
- `src/keywharf/commands/`: Typer command adapters
- `src/keywharf/config/`: formal config loading and resolution
- `src/keywharf/config_defaults/`: package-shipped JSON defaults
- `src/keywharf/templates/`: package-shipped JSON and Jinja resources
- `src/keywharf/services/`: workflow logic
- `src/keywharf/storage/`: file/state/git persistence helpers
- `src/keywharf/ssh_config/`: SSH parse/build/render logic
- `src/keywharf/runtime/`: workspace discovery helpers
- `docs/`: project docs
- `tests/`: test suite

## Running

From source:

```bash
PYTHONPATH=src python -m keywharf --help
```

Installed entrypoint:

```bash
keywharf --help
```

## Tests

Run the full suite:

```bash
pytest
```

Current coverage includes:

- CLI help/version and final command set
- config defaults loading and deep-merge contract
- runtime path resolution and workspace discovery
- package-resource-driven `init`
- package `.j2` loading and rendering
- repo host CRUD
- state persistence
- validation and selector stability
- render no-write behavior
- apply orchestration and safety guards
- include detection/installation
- privilege helper and sudo re-exec flow
- thin import surfaces

## Config Development Rules

Manager config follows the formal runtime config pattern:

- defaults live in package JSON resources
- file or mapping input is override only
- merge happens before validation
- runtime path resolution is explicit and separate

Do not reintroduce:

- hard-coded operational defaults scattered across model fields
- runtime path expansion during raw config load
- repo-root example config directories
- alternate env vars, markers, package names, or other naming shims

## Template Rules

- JSON package resources hold formal defaults and structured starter data
- `.j2` resources are only for text scaffolding
- `importlib.resources` and package loaders must work in editable installs and built distributions

## Command And Service Boundaries

- keep CLI modules thin
- keep privilege checks centralized
- keep services free of Rich/Typer concerns
- keep storage free of CLI concerns
- keep the main SSH config outside normal write paths
- keep host definition editing limited to the host repo unless a later phase explicitly expands that scope

## Packaging

- all metadata and dependencies live in `pyproject.toml`
- version comes from `keywharf.version.__version__`
- package resources ship through setuptools package-data rules
- root package `__init__.py` stays intentionally thin and does not re-export version or service symbols

## Hygiene

Keep generated noise out of the repository:

- `__pycache__/`
- `.pytest_cache/`
- `*.egg-info/`
- `build/`
- `dist/`
