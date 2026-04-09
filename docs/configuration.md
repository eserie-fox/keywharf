# Configuration

## Data Root Resolution

Canonical naming is `SSH_MANAGER_DATA_ROOT`.

Resolution order:

1. environment variable `SSH_MANAGER_DATA_ROOT`
2. marker file `SSH_MANAGER_DATA_ROOT`
3. legacy environment variable `SSH_CONFIG_DATA_ROOT`
4. legacy marker file `SSH_CONFIG_DATA_ROOT`

Marker search looks at the current working directory, its parents, the user home directory, and direct child directories of those candidates.

## Manager Config

Manager config is a JSON object, typically stored at `<data-root>/config.json`.

Fields:

- `ssh_key_remote_repo`: git remote URL for the SSH key/config repo
- `ssh_key_local_repo`: local checkout path for that repo
- `ssh_dir`: base SSH directory
- `managed_config_path`: manager-owned SSH config fragment path
- `managed_keys_dir`: manager-owned copied key directory
- `state_path`: local desired-state file path

Example:

```json
{
  "ssh_key_remote_repo": "git@your.git.server:org/keys.git",
  "ssh_key_local_repo": "%{DATA_ROOT}/repos/keys",
  "ssh_dir": "~/.ssh",
  "managed_config_path": "~/.ssh/managed/ssh-manager.conf",
  "managed_keys_dir": "~/.ssh/managed/keys",
  "state_path": "%{DATA_ROOT}/state/state.json"
}
```

Path behavior:

- `%{DATA_ROOT}` expands to the resolved data root
- `~` and environment variables are expanded
- relative paths resolve from the manager config directory

Defaults when fields are omitted:

- `main_config_path = <ssh_dir>/config`
- `managed_config_path = <ssh_dir>/managed/ssh-manager.conf`
- `managed_keys_dir = <ssh_dir>/managed/keys`
- `state_path = <data-root>/state/state.json`

## Local State Schema

`state_path` is the desired source of truth:

```json
{
  "version": 1,
  "selected_hosts": [
    {
      "server_name": "demo",
      "endpoint_name": "public",
      "authentication_name": "home"
    }
  ]
}
```

Rules:

- one `ServerName` maps to at most one local selection entry
- `endpoint_name` and `authentication_name` may be `null` only when the remote host still has exactly one endpoint/authentication option
- state must be serializable and atomic-written through storage helpers
- state does not store rendered SSH text or copied-key payloads

## Remote Repo Config and Selector Rules

The remote repo still uses `config.json` in the repo root and keeps the existing schema.

Each entry contains:

- `ServerName`
- optional `Comment`
- `Endpoint`
- `Authentication`
- optional `ExtraConfig`

Stage three adds stricter validation on selector stability:

- `ServerName` must be unique
- when a host has multiple `Endpoint` entries, every entry must have a unique `EndPointName`
- when a host has multiple `Authentication` entries, every entry must have a unique `AuthenticationName`
- local state selectors must resolve uniquely against the current remote repo
- a previously valid `null` selector becomes invalid once the remote host grows from one option to multiple options

## Ownership Boundary

ssh-manager now manages:

- `managed_config_path`
- `managed_keys_dir`
- `state_path`
- the main SSH config only when `install-include` is explicitly run

ssh-manager does not manage:

- unrelated user `Host` entries in `<ssh_dir>/config`
- `Match` blocks
- other `Include` directives
- user comments and ordering in the main config

## Managed Output Behavior

- `select` / `deselect` update only `state_path`
- `render` resolves state and prints the desired managed config preview without writing files
- `apply` validates, renders, copies manager-owned keys, atomically replaces `managed_config_path`, and removes stale managed keys
- `local list/show` compare state with the current managed output and expose `applied`, `pending`, `invalid`, and `orphaned`

The main config is not the source of truth, and the managed config is not the source of truth either. The state file is.

## `install-include` Semantics

`install-include` is the explicit command for attaching the manager-owned fragment to OpenSSH.

Behavior:

- default target is `<ssh_dir>/config`
- scans only top-level `Include` lines
- ignores commented lines
- treats exact path matches and glob coverage of `managed_config_path` as already installed
- if the main config does not exist, creates a minimal file containing only the ssh-manager include block
- if the main config exists and lacks the include, appends a small include block at EOF
- supports `--dry-run`

Other commands do not modify the main config.

## Validation and Safety Guards

`validate` now covers:

- manager config loading
- remote repo schema and identity-file existence
- state schema and selector stability
- warnings for missing include installation
- warnings for orphaned managed hosts

`apply` adds a safety guard:

- if local state is empty but `managed_config_path` still contains hosts, `apply` fails by default
- `--allow-empty` is required to intentionally clear a non-empty managed config

## Compatibility Notes

- `SSH_MANAGER_DATA_ROOT` is the documented name going forward
- legacy `SSH_CONFIG_DATA_ROOT` is still accepted
- recommended commands are now `init`, `validate`, `render`, `apply`, `select`, and `deselect`
- compatibility aliases remain:
  - `add -> select`
  - `remove -> deselect`
  - `check -> validate`
  - `flush -> apply`
- no automatic migration is performed for stage-two setups that used `managed_config_path` as implicit state
