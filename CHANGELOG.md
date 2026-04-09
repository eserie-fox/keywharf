# Changelog

## Unreleased

- finalized the project on the new command model: `init`, `pull`, `validate`, `render`, `apply`, `install-include`, `select`, `deselect`, `remote`, and `local`
- removed all legacy compatibility commands, facades, aliases, and repo-root example config files
- formalized manager config with Pydantic v2, package-shipped defaults, deep-merge loading, and explicit runtime resolution
- changed `init` to use package resources instead of repository example files
- kept the manager-owned ownership boundary: managed config fragment, managed keys, and explicit include installation only
- replaced GitPython with system `git` subprocess execution
- added centralized privilege preflight and `--sudo` full-command re-exec for mutating commands
- rewrote docs and tests to describe and validate only the final model
