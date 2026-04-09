# Configuration

## Data Root Resolution

Canonical naming in this phase is `SSH_MANAGER_DATA_ROOT`.

Resolution order:

1. environment variable `SSH_MANAGER_DATA_ROOT`
2. marker file `SSH_MANAGER_DATA_ROOT`
3. legacy environment variable `SSH_CONFIG_DATA_ROOT`
4. legacy marker file `SSH_CONFIG_DATA_ROOT`

Marker search looks at the current working directory, its parents, the user home directory, and direct child directories of those candidates.

## Manager Config

The manager config is a JSON object, typically stored at `<data-root>/config.json`.

Current fields:

- `ssh_key_remote_repo`: git remote URL for the SSH key/config repo
- `ssh_key_local_repo`: local checkout path for that repo
- `ssh_dir`: SSH directory containing the managed `config` file

Example:

```json
{
  "ssh_key_remote_repo": "git@your.git.server:org/keys.git",
  "ssh_key_local_repo": "%{DATA_ROOT}/repos/keys",
  "ssh_dir": "~/.ssh"
}
```

Path behavior:

- `%{DATA_ROOT}` expands to the resolved data root
- `~` and environment variables are expanded
- relative paths resolve from the manager config file directory

## Remote Repo Config

The remote repo still uses `config.json` in the repo root and keeps the existing schema for this phase.

Each entry is a server definition with:

- `ServerName`
- optional `Comment`
- `Endpoint`: list of endpoint choices
- `Authentication`: list of authentication choices
- optional `ExtraConfig`

This refactor does not change that schema.

## Local SSH Config Behavior

- `add` still generates a `Host` block from one remote endpoint/authentication choice
- copied identity files still land under `<ssh_dir>/<server_name>/`
- `remove` still deletes the copied identity file and prunes the empty per-host directory
- `flush` still rewrites the managed local SSH config with atomic replace and optional backup

## `check` Semantics

`check` is validation-only in this phase.

It verifies:

- the remote config JSON loads successfully
- the config is not empty
- each server has a non-empty `ServerName`
- each referenced `IdentityFile` exists relative to the local repo checkout

It does not:

- sort the remote config
- rewrite `config.json`
- create `.bak` files

## Compatibility Notes

- `SSH_MANAGER_DATA_ROOT` is the documented name going forward
- legacy `SSH_CONFIG_DATA_ROOT` is still accepted
- command names remain `pull`, `local`, `remote`, `add`, `remove`, `flush`, and `check`
