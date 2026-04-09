# Development

## Prerequisites

- Python 3.11+
- a virtual environment is recommended

Typical setup:

```bash
python3.11 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
```

## Repository Layout

- `src/ssh_manager/`: package source
- `docs/`: architecture, configuration, and development notes
- `tests/`: CLI/runtime/service regression coverage
- `config_example/`: example manager and remote repo configs

## Running the CLI From Source

Use:

```bash
PYTHONPATH=src python -m ssh_manager --help
```

Installed entrypoints continue to use `ssh-manager`.

## Tests

Run the full suite with:

```bash
pytest
```

Useful focused runs:

```bash
pytest tests/test_cli.py
pytest tests/test_runtime.py
pytest tests/test_check_service.py
```

Current baseline coverage includes:

- CLI help and version startup
- config path resolution
- data-root resolution precedence
- version source consistency
- `check` pure-validation behavior

## Packaging

- setuptools now uses standard `src` layout
- version is loaded dynamically from `ssh_manager.version.__version__`
- do not reintroduce duplicate version constants in source and `pyproject.toml`

## Hygiene

- keep generated artifacts such as `*.egg-info`, `__pycache__`, `build/`, and `dist/` out of the repository
- do not reintroduce import-time data-root resolution side effects
- keep CLI code thin; new business logic should normally land in `services/`
