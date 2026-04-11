# Configuration

## Workspace Discovery

Discovery order:

1. explicit `--workspace`
2. `KEYWHARF_WORKSPACE`
3. search `cwd`, each ancestor, then `~`
4. for each base directory: scan one level of child directories first
5. then check the base directory itself
6. the first directory containing `KEYWHARF_WORKSPACE` wins
7. fail with a message listing the checked directories

The discovery path is strict on purpose:

- no recursive child scanning
- no fixed home workspace fallback
- no alias env vars or alias markers
- marker presence decides the workspace root; missing `config.json` is a later config-load error

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

- `host_repo_remote_url`
- `host_repo_path`
- `ssh_dir`
- `managed_config_path`
- `managed_keys_dir`
- `state_path`

Defaults resource:

```json
{
  "host_repo_remote_url": null,
  "host_repo_path": "%{WORKSPACE}/repo",
  "ssh_dir": "~/.ssh",
  "managed_config_path": null,
  "managed_keys_dir": null,
  "state_path": "%{WORKSPACE}/state/state.json"
}
```

By default, `%{WORKSPACE}/repo` is the one host repo directory under the workspace.

Resolver-derived defaults:

- `managed_config_path -> <ssh_dir>/managed/keywharf.conf`
- `managed_keys_dir -> <ssh_dir>/managed/keys`
- `main_config_path -> <ssh_dir>/config`

## Runtime Resolution

Raw config is not resolved during load/merge/validate.

Runtime resolution happens in `resolve_manager_config(...)`:

- `%{WORKSPACE}` expands to the resolved workspace root
- `~` expands to home
- environment variables expand
- relative paths resolve from the manager config directory

If both `--workspace` and an absolute `--config` path are supplied, the absolute config must live under the chosen workspace root.

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
- `endpoint_name` and `authentication_name` are optional name-based selector fields
- `endpoint_name` may be `null` only for a singleton endpoint set
- `authentication_name` may be `null` only for a singleton authentication set

## Host Repo Config

The host repo still uses `config.json` in the repo root. With the default config, that repo root is `%{WORKSPACE}/repo`.

Validation rules:

- `ServerName` must be present and unique
- if a host has multiple endpoints, each endpoint needs a unique `EndPointName`
- if a host has multiple authentication options, each authentication needs a unique `AuthenticationName`
- endpoint `Comment` is preserved
- authentication `Comment` is preserved
- referenced identity files must exist in the host repo
- state selectors must resolve uniquely against the current host repo

`repo init` bootstraps a local-first repo skeleton with:

- empty `config.json`
- `keys/`
- `.gitignore`

`keywharf init` creates `%{WORKSPACE}/repo` as an empty directory. `repo init` then writes this skeleton there. It does not run `git init` or create `.git`.

`repo host add/update/remove`, `repo host endpoint ...`, and `repo host auth ...` edit only this host repo file. They do not commit, push, or initialize git.

Current edit boundary:

- host shells support `Comment`
- endpoints support stable `EndPointName`, `HostName`, optional `Port`, and optional `Comment`
- authentication options support stable `AuthenticationName`, optional `User`, optional `IdentityFile`, and optional `Comment`
- `repo host add` creates a host shell only
- `repo host endpoint add` is how endpoints are added later
- `repo host auth add` is how authentication options are added later
- `select` writes name-based endpoint/authentication selectors into local state; singleton selections may leave those fields `null`
- `validate` reports every host shell missing endpoint options, authentication options, or both
- `render` and `apply` only require selected hosts to be complete
- `ExtraConfig` is preserved but not exposed as CLI CRUD yet

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
