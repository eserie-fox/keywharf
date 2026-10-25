# Keywharf development

- Keep commands as thin Typer adapters, services as orchestration, storage as I/O, and SSH
  construction/parsing/rendering structure-driven. Keep package import surfaces thin.
- `ServerName` is the canonical management identifier and managed-key owner. Shared `Aliases`
  declare available literal SSH names; local v2 `host_names` explicitly enables a non-empty subset.
  Only `select` discovers a canonical host from a name/address query before the normal selection
  workflow. Other management selectors and persisted references stay canonical. Never infer
  ownership from the query or first SSH name; discovery never enables names or chooses an endpoint.
- Keep the v1 state adapter at the input boundary. Only select/deselect persist selections;
  apply materializes artifacts. Reads must not migrate or create state.
- Managed blocks carry reserved canonical ownership comments. Diagnose ambiguous ownership before
  building maps. Copy required keys before replacing config; delete stale keys only afterward.
- Validate namespace structure even for unselected shells. Repo-wide completeness belongs to
  validate; render/apply require only selected definitions to be complete. Preserve shared ordering.
- Run `make check` (Ruff format, Ruff lint, pytest), `uv run mypy src/keywharf`, and relevant
  installed-package resource checks. Test aliases with `pytest tests/test_aliases.py`.
- Test domain state and reparsed arguments, not terminal wording or serialized argument layout.
  Keep distinct behavioral coverage; enforce invariants in code rather than explanatory comments.
- Use synthetic fixtures and explicitly isolated workspaces with `ssh_dir` and every managed path
  redirected inside them. Never use automatic workspace discovery for development smoke tests.
- Do not operate on real SSH keys, remote servers, DNS, private definitions, or adjacent projects.
