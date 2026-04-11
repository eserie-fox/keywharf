# Changelog

## Unreleased

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
