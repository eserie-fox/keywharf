# Configuration

## Data Root Resolution

The final project uses one canonical data-root name only:

- environment variable: `SSH_MANAGER_DATA_ROOT`
- marker file: `SSH_MANAGER_DATA_ROOT`

Resolution order:

1. `SSH_MANAGER_DATA_ROOT`
2. nearest `SSH_MANAGER_DATA_ROOT` marker from `cwd` upward
3. `SSH_MANAGER_DATA_ROOT` marker in `home`

## Formal Manager Config

Manager config is a Pydantic v2 model loaded with a fixed pipeline:

1. read defaults from `pkg://ssh_manager/config_defaults/manager.json`
2. read one file or mapping override
3. deep-merge
4. `model_validate`

Available constructors:

- `ManagerConfig.from_defaults()`
- `ManagerConfig.from_file(path)`
- `ManagerConfig.from_mapping(data)`

Deep-merge contract:

- mapping + mapping: recursive merge
- all other types: override replaces base
- no list concatenation
- no implicit type magic

## Raw Config Schema

Fields:

- `ssh_key_remote_repo`
- `ssh_key_local_repo`
- `ssh_dir`
- `managed_config_path`
- `managed_keys_dir`
- `state_path`

Defaults resource:

```json
{
  "ssh_key_remote_repo": "git@example.com:org/keys.git",
  "ssh_key_local_repo": "%{DATA_ROOT}/repos/keys",
  "ssh_dir": "~/.ssh",
  "managed_config_path": null,
  "managed_keys_dir": null,
  "state_path": "%{DATA_ROOT}/state/state.json"
}
```

`managed_config_path` and `managed_keys_dir` default in the resolver, not in field defaults:

- `managed_config_path -> <ssh_dir>/managed/ssh-manager.conf`
- `managed_keys_dir -> <ssh_dir>/managed/keys`

## Runtime Resolution

Raw config is not resolved during load/merge/validate.

Runtime resolution happens in `resolve_manager_config(...)` and produces absolute paths.

Resolution rules:

- `%{DATA_ROOT}` expands to resolved data root
- `~` expands to home
- environment variables expand
- relative paths resolve from the manager config directory

`main_config_path` is derived only at runtime:

- `<ssh_dir>/config`

## State File

`state_path` is the desired source of truth.

Schema:

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

- one `ServerName` maps to at most one state entry
- selectors are name-based, not index-based
- `endpoint_name` may be `null` only for a singleton endpoint set
- `authentication_name` may be `null` only for a singleton authentication set

## Remote Repo Constraints

Remote repo still uses `config.json` in the repo root.

Validation rules enforced by `validate`:

- `ServerName` must be present and unique
- if a host has multiple endpoint options, every endpoint needs a unique `EndPointName`
- if a host has multiple authentication options, every authentication needs a unique `AuthenticationName`
- referenced identity files must exist in the local repo checkout
- state selectors must resolve uniquely against the current remote repo

## Managed Output

`render` produces:

- managed SSH config text
- resolved host selections
- planned key copies
- planned stale-key deletions

`apply` then:

1. validates
2. renders
3. copies new managed keys
4. atomically replaces `managed_config_path`
5. deletes stale managed keys

Safety rule:

- if state is empty while `managed_config_path` still contains hosts, `apply` fails by default
- `--allow-empty` is required to intentionally clear it

## Include Installation

`install-include` is the only command that may modify the main SSH config.

Behavior:

- target is `<ssh_dir>/config`
- exact include match or glob coverage counts as already installed
- if absent, append one minimal include block
- `--dry-run` previews without writing

## Ownership Summary

Managed by `ssh-manager`:

- `managed_config_path`
- `managed_keys_dir`
- `state_path`

Not managed by `ssh-manager`:

- unrelated user `Host` blocks
- `Match` blocks
- other `Include` lines
- comments and order in the main SSH config

