# Changelog

## Unreleased

- refactored the project into a standard `src/ssh_manager/` layout
- split CLI adapters from service, storage, domain, runtime, and SSH config logic
- unified version sourcing through `ssh_manager.version.__version__`
- raised the supported Python floor to 3.11 to match actual syntax usage
- standardized canonical data-root naming on `SSH_MANAGER_DATA_ROOT` while keeping legacy `SSH_CONFIG_DATA_ROOT` compatibility
- changed `check` to pure validation with no rewrite or backup side effects
- changed ownership from whole-main-config rewrites to a manager-owned config fragment plus managed keys
- added explicit `install-include` support for connecting the managed fragment to OpenSSH
- added explicit local desired state at `state_path` and made it the source of truth for selected hosts
- introduced `init`, `validate`, `render`, `apply`, `select`, and `deselect` as the recommended command model
- changed `add/remove/flush/check` into compatibility aliases that map to the new workflow
- added selector-stability validation based on `ServerName`, `EndPointName`, and `AuthenticationName`
- added apply safety guards so empty state does not clear an existing managed config unless `--allow-empty` is passed
- added docs for architecture, configuration, and development
- added docs for the stage-three CLI workflow
- added baseline tests for CLI startup, runtime path resolution, version consistency, state persistence, validation, render, apply, and compatibility mappings
