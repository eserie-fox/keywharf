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
- `docs/`: architecture, configuration, CLI, and development notes
- `tests/`: CLI/runtime/service regression coverage
- `config_example/`: example manager and remote repo configs

## Running From Source

```bash
PYTHONPATH=src python -m ssh_manager --help
```

Installed entrypoints continue to use `ssh-manager`.

## Test Suite

Run the full suite with:

```bash
pytest
```

Useful focused runs:

```bash
pytest tests/test_cli.py
pytest tests/test_runtime.py
pytest tests/test_init.py
pytest tests/test_state_store.py
pytest tests/test_validate_service.py
pytest tests/test_render_service.py
pytest tests/test_apply_service.py
pytest tests/test_select_commands.py
pytest tests/test_local_commands.py
pytest tests/test_install_include.py
pytest tests/test_managed_config.py
pytest tests/test_check_service.py
```

Current baseline coverage includes:

- CLI help/version and compatibility alias help
- config path resolution and data-root precedence
- `init` workspace skeleton creation
- explicit state load/save behavior
- selector stability and validation failures
- preview-only render behavior
- apply orchestration, atomic managed-config replacement, and empty-state guardrails
- include detection and installation behavior
- protection against accidental main-config modification

## Packaging

- setuptools uses standard `src` layout
- version is loaded dynamically from `ssh_manager.version.__version__`
- do not reintroduce duplicate version constants in source and `pyproject.toml`

## Development Guidelines

- keep CLI adapters thin; new business logic should land in `services/`
- keep state and desired-output logic separate from file materialization
- do not reintroduce “managed config as source of truth”
- keep the main SSH config outside ssh-manager’s normal write path; only `install-include` may modify it
- avoid import-time data-root side effects

## Hygiene

- keep generated artifacts such as `*.egg-info`, `__pycache__`, `.pytest_cache`, `build/`, and `dist/` out of the repository
- keep docs aligned with the current command model and state schema whenever behavior changes
