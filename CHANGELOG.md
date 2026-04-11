# Changelog

## Unreleased

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
