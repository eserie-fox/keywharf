# Changelog

## Unreleased

## 1.0.6 (2026-08-30)

- replace hand-written Git subprocess orchestration with GitPython's repository and remote object APIs
- retain system Git authentication, noninteractive SSH behavior, exact origin matching, and fast-forward-only pulls
- support linked worktrees while requiring the configured path to be the exact worktree root
- sanitize Git command failures, redact embedded URL credentials, and close every opened or cloned repository explicitly
- add the security-sensitive `GitPython>=3.1.59,<4` runtime constraint and local-only Git regression coverage
- harden tag-authoritative publication by validating the deterministic build epoch and ignoring tag deletion or move events
- migrate distribution license metadata to the standardized PEP 639 fields
- bump runtime/package version metadata to `1.0.6` and add patch-release documentation

## 1.0.5 (2026-06-02)

- removed runtime reliance on external `click` imports so Typer 0.26+ environments that use vendored Click no longer fail during CLI startup
- made sudo retry invocation serialization compatible with Typer-style argument and option parameter objects without external Click type checks
- kept interactive `select` prompting behavior while replacing `click.IntRange` and `click.get_text_stream` usage with Typer-facing APIs and local range validation
- added regression coverage for Typer-like invocation parameters and a dependency-scan test that catches undeclared direct runtime imports
- raised the runtime Typer baseline to `typer>=0.26`, raised Rich to `rich>=13.8`, and changed runtime dependencies to minimum-only constraints with no upper bounds
- added explicit Ruff configuration for Python 3.11, 100-column formatting, import sorting, Python upgrade checks, Bugbear checks, and Ruff-specific checks
- raised dev dependency floors to `pytest>=8` and `ruff>=0.14` while keeping minimum-only dependency constraints
- fixed release-check hygiene issues so full `ruff format --check .` and `ruff check .` can pass on the Python 3.11+ codebase
- bumped runtime/package version metadata to `1.0.5` and added release documentation

## 1.0.4 (2026-04-12)

- added high-frequency read-only convenience facade commands: `keywharf list repo`, `keywharf show repo <server>`, `keywharf list local`, and `keywharf show local <server>`
- kept canonical paths as the primary command tree: `keywharf repo host list/show` and `keywharf local list/show`; convenience commands forward to canonical handlers without introducing a second business implementation
- kept convenience boundaries explicit: only `repo` (host definitions in the host repo) and `local`, read-only only, with no convenience facade for endpoint/auth or write operations
- aligned CLI help text plus README/CLI docs with the convenience-versus-canonical relationship
- added convenience parity and help-boundary tests, and bumped runtime/package version metadata to `1.0.4`

## 1.0.3 (2026-04-11)

- added interactive `select` completion for multi-endpoint and multi-authentication hosts in TTY terminals while keeping explicit stable-name selection unchanged
- made noninteractive `select` failures explicit by requiring `--endpoint <stable_name>` and `--auth <stable_name>` when multiple choices exist
- cleaned up top-level `KeywharfError` exits so expected CLI errors print without extra traceback noise
- aligned README, CLI, configuration, and workspace-template docs with current `select` behavior and name-based state semantics, including singleton `null` selectors
- bumped version metadata to `1.0.3`, added release notes, and added a small release-doc entrypoint

## 1.0.2 (2026-04-11)

- finalized the project on the current command model: `init`, `repo init`, `repo sync`, `validate`, `render`, `apply`, `install-include`, `select`, `deselect`, `repo host ...`, and `local`
- removed all legacy compatibility commands, facades, aliases, and repo-root example config files
- formalized manager config with Pydantic v2, package-shipped defaults, deep-merge loading, and explicit runtime resolution
- changed `init` to use package resources instead of repository example files
- kept the manager-owned ownership boundary: managed config fragment, managed keys, and explicit include installation only
- replaced GitPython with system `git` subprocess execution
- added centralized privilege preflight and `--sudo` full-command re-exec for mutating commands
- added host management layering for endpoint/auth option editing, comment support, and stable selector names in local state
- rewrote docs and tests to describe and validate only the final model
- finalized 1.0.2 release closure by aligning version metadata with the single-source runtime version
- started publishing per-version release notes under `docs/release-notes/` from `1.0.2`
