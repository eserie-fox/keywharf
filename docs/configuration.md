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

When `host_repo_remote_url` is configured, `repo sync` requires exact equality with the checkout's `origin` URL. It uses
GitPython over system Git and keeps system HTTPS credentials, SSH agents, SSH configuration, and known-hosts behavior.

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
  "version": 2,
  "selected_hosts": [
    {
      "server_name": "demo-node-01",
      "host_names": ["demo-node-01", "dev"],
      "endpoint_name": "direct",
      "authentication_name": "developer"
    }
  ]
}
```

Rules:

- one canonical `ServerName` maps to at most one state entry
- `host_names` is required in v2: a non-empty, duplicate-free list of declared literal names
- enabled names must match declared spelling exactly; canonical name comes first when selected,
  followed by aliases sorted case-insensitively (the shared definition arrays keep their declared order)
- canonical-only, alias-only, and canonical-plus-alias selections share one endpoint/authentication
  choice, one block, and one canonical managed-key directory
- adding a shared alias never enables it on an existing client
- removing an enabled alias makes the selection invalid until explicitly replaced using `--name`
- selectors are name-based, not index-based
- `endpoint_name` and `authentication_name` are optional name-based selector fields
- `endpoint_name` may be `null` only for a singleton endpoint set
- `authentication_name` may be `null` only for a singleton authentication set

## Host Repo Config

The host repo still uses `config.json` in the repo root. With the default config, that repo root is `%{WORKSPACE}/repo`.

Validation rules:

- `ServerName` must be present and unique; it remains the management identifier
- optional `Aliases` defaults to `[]`; an explicit value must be a list of strings, never `null`
- canonical names and aliases share one case-insensitive repository namespace, including unselected
  shells; duplicate aliases and aliases repeating their own canonical name are errors
- spelling is preserved: names such as `Demo_NODE-01.test` are valid
- literal names start with an ASCII letter, digit, or underscore and contain only ASCII letters,
  digits, underscores, hyphens, and dots; trailing dots and Windows device names are rejected
- whitespace, control characters, SSH patterns/negation, quotes, comments, and paths are rejected;
  the canonical name must also be safe as a managed-key directory component
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

- host shells support `Comment` and `Aliases`
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

## Shared Aliases and Explicit Selection

```json
{
  "ServerName": "demo-node-01",
  "Aliases": ["dev", "work"],
  "Endpoint": [
    {"EndPointName": "direct", "HostName": "demo-node-01.example.invalid", "Port": 22}
  ],
  "Authentication": [
    {"AuthenticationName": "developer", "User": "developer", "IdentityFile": "keys/demo_ed25519"}
  ]
}
```

`keywharf select demo-node-01 --endpoint direct --auth developer --name dev` enables only `dev`.
Management commands still take `demo-node-01`, including `deselect` and `local show`.

With `managed_keys_dir` set to `/tmp/keywharf-demo/ssh/managed/keys`, this selection renders:

```sshconfig
# keywharf-owner: demo-node-01
Host dev
    HostName demo-node-01.example.invalid
    Port 22
    User developer
    IdentityFile /tmp/keywharf-demo/ssh/managed/keys/demo-node-01/demo_ed25519
```

The reserved ownership comment is separate from human comments. Do not edit it or use
`keywharf-owner` as a human comment prefix. It keeps alias-only and disjoint name sets attached to
one canonical definition. Keywharf reads its previous single-name blocks without this comment;
multiple names without ownership, duplicate owners, and overlapping blocks are errors.

## State Upgrade and Coordinated Rollout

Upgrade **every client and repo editor before adding shared aliases or changing private canonical
or endpoint names**. Software installation alone does not rewrite state or shared definitions.
Keep original files for coordinated restoration before changing shared data.

The sole legacy adapter accepts v1 (including the original missing-version form) and adds
`host_names: [server_name]` in memory. Endpoint/authentication selectors, including singleton `null`
values, are unchanged. It does not infer renames, choose new connection options, or enable aliases.
V1 carrying `host_names` is inconsistent and rejected. V2 missing/null/empty `host_names`, malformed
name lists, and unsupported versions are errors.

Before, v1:

```json
{"version": 1, "selected_hosts": [{"server_name": "demo-node-01", "endpoint_name": null, "authentication_name": null}]}
```

After a successful state-writing command, v2:

```json
{"version": 2, "selected_hosts": [{"server_name": "demo-node-01", "host_names": ["demo-node-01"], "endpoint_name": null, "authentication_name": null}]}
```

`render`, `validate`, local/repo views, and dry runs never create, rewrite, or back up state.
`apply` writes managed artifacts only and does not migrate state. The next successful `select` or
`deselect` atomically saves v2 for **all retained entries**; initialization also creates v2. With
unnamed singleton endpoint/authentication options, this disposable-workspace sequence demonstrates
the example transition (set every manager path, including `ssh_dir`, inside that workspace first):

```bash
keywharf --workspace /tmp/keywharf-demo render
# state remains v1
keywharf --workspace /tmp/keywharf-demo select demo-node-01 --name demo-node-01
# state is now v2; singleton selectors remain null
```

The inspected pre-change 1.0.6 baseline (`be48dd2`) explicitly checks the loaded state version and
rejects v2. This does not establish behavior for unexamined historical releases. That baseline drops
`Aliases` during host model serialization and does not understand canonical ownership metadata:
rejection of v2 state does **not**
make old editors safe for alias-bearing repositories or new managed output. Downgrading requires
coordinated restoration of compatible original repo, state, and managed files, plus any required
keys. Changing only the version number loses the intended contract and is not a downgrade procedure.

Renaming `ServerName` changes the management identifier and canonical key directory. Keeping the
old name in `Aliases` does not repair old `server_name` references. Clients must explicitly deselect
the old identifier, select the new definition with valid names and connection choices, then apply.
Private node renames, endpoint-label normalization, and client file migration require a separate
coordinated change using those actual files.
