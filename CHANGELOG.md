# Changelog

## Unreleased

- refactored the project into a standard `src/ssh_manager/` layout
- split CLI adapters from service, storage, domain, runtime, and SSH config logic
- unified version sourcing through `ssh_manager.version.__version__`
- raised the supported Python floor to 3.11 to match actual syntax usage
- standardized canonical data-root naming on `SSH_MANAGER_DATA_ROOT` while keeping legacy `SSH_CONFIG_DATA_ROOT` compatibility
- changed `check` to pure validation with no rewrite or backup side effects
- added docs for architecture, configuration, and development
- added baseline tests for CLI startup, runtime path resolution, version consistency, and `check` purity
