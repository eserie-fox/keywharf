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

- `src/ssh_manager/`: package source
- `src/ssh_manager/commands/`: Typer command adapters
- `src/ssh_manager/config/`: formal config loading and resolution
- `src/ssh_manager/config_defaults/`: package-shipped JSON defaults
- `src/ssh_manager/templates/`: package-shipped init templates
- `src/ssh_manager/services/`: application logic
- `src/ssh_manager/storage/`: file/state/git persistence helpers
- `src/ssh_manager/ssh_config/`: SSH parse/build/render logic
- `docs/`: project docs
- `tests/`: test suite

## Running

From source:

```bash
PYTHONPATH=src python -m ssh_manager --help
```

Installed entrypoint:

```bash
ssh-manager --help
```

## Tests

Run the full suite:

```bash
pytest
```

Current test coverage includes:

- CLI help/version and final command set
- formal config defaults loading and merge contract
- runtime path resolution and data-root discovery
- package-resource-driven `init`
- state persistence
- validation and selector stability
- render no-write behavior
- apply orchestration and safety guards
- include detection/installation
- privilege helper and sudo re-exec flow
- package resource availability
- thin import surfaces

## Config Development Rules

Manager config follows the formal runtime config pattern:

- defaults live in package JSON resources
- file or mapping input is override only
- merge happens before validation
- runtime path resolution is explicit and separate

Do not reintroduce:

- hard-coded operational defaults scattered across field defaults
- runtime path expansion during raw config load
- repo-root example config directories

## Command/Service Boundaries

- keep CLI modules thin
- keep privilege checks centralized
- keep services free of Rich/Typer concerns
- keep storage free of CLI concerns
- keep the main SSH config outside normal write paths

## Packaging

- all metadata and dependencies live in `pyproject.toml`
- version comes from `ssh_manager.version.__version__`
- package resources are shipped through setuptools package-data rules

## Hygiene

Keep generated noise out of the repository:

- `__pycache__/`
- `.pytest_cache/`
- `*.egg-info/`
- `build/`
- `dist/`

