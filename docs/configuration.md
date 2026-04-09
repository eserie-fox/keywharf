# Configuration

## Workspace Discovery

`keywharf` uses one canonical workspace name only:

- environment variable: `KEYWHARF_DATA_ROOT`
- marker file: `KEYWHARF_DATA_ROOT`

Discovery order:

1. explicit `--data-root`
2. `KEYWHARF_DATA_ROOT`
3. current directory, if it already contains both the marker and `config.json`
4. nearest ancestor directory with a usable marker/config pair
5. fixed home candidate `~/keywharf`
6. fail with a message listing the attempted candidates

The discovery path is strict on purpose:

- no recursive home scanning
- no fuzzy directory guessing
- no alias env vars or alias markers

## Formal Manager Config

Manager config is a Pydantic v2 model loaded with one fixed pipeline:

1. read defaults from `pkg://keywharf/config_defaults/manager.json`
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

Resolver-derived defaults:

- `managed_config_path -> <ssh_dir>/managed/keywharf.conf`
- `managed_keys_dir -> <ssh_dir>/managed/keys`
- `main_config_path -> <ssh_dir>/config`

## Runtime Resolution

Raw config is not resolved during load/merge/validate.

Runtime resolution happens in `resolve_manager_config(...)`:

- `%{DATA_ROOT}` expands to the resolved workspace root
- `~` expands to home
- environment variables expand
- relative paths resolve from the manager config directory

If both `--data-root` and an absolute `--config` path are supplied, the absolute config must live under the chosen data root.

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

## Remote Repo Config

The local checkout still uses `config.json` in the repo root.

Validation rules:

- `ServerName` must be present and unique
- if a host has multiple endpoints, each endpoint needs a unique `EndPointName`
- if a host has multiple authentication options, each authentication needs a unique `AuthenticationName`
- referenced identity files must exist in the local repo checkout
- state selectors must resolve uniquely against the current remote repo

`remote host add/update/remove` edit only this local checkout file. They do not commit or push.

Current edit boundary:

- Host-level CRUD only
- one new host is created with one endpoint and one authentication entry
- `ExtraConfig` is preserved but not exposed as CLI CRUD yet
- when a host has multiple endpoint/auth options, `remote host update` requires `--target-endpoint` / `--target-auth`

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

## Package Resources And Templates

Package resources are split by role:

- `config_defaults/*.json`: formal defaults
- `templates/*.json`: structured starter data
- `templates/*.j2`: text scaffolding

Current `.j2` usage includes:

- workspace `README.md`
- workspace `.gitignore`
- include block text

Manager config and state files remain structured JSON writes, not template-rendered text.
