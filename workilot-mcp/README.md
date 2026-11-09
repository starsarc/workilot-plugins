# Workilot MCP Plugin

This plugin documents the Codex-native Workilot MCP connection and the repository-level project binding workflow.

## Install

```bash
codex plugin marketplace add starsarc/workilot-plugins
codex plugin add workilot-mcp@workilot
```

Plugin distribution: https://github.com/starsarc/workilot-plugins. The main Workilot
application remains on GitArk; this GitHub repository contains only plugins.

Requires Codex with plugin support, Git, and Python 3.10 or later. See the
[installation guide](../README.md#install-in-codex) for prerequisites, offline installation, and updates.

## Configure Codex

Create a Workilot Agent API key with the required MCP scopes and capabilities. Keep the key
available to the Codex process as `WORKILOT_MCP_TOKEN`; do not paste the key into chat, commit
it, or place it in a repository file. Register the deployed Streamable HTTP endpoint with Codex:

```bash
codex mcp add workilot \
  --url "https://<workilot-host>/mcp" \
  --bearer-token-env-var WORKILOT_MCP_TOKEN
```

The URL is written literally to Codex's configuration; `bearer_token_env_var` keeps the key out
of that file. Codex owns the connection and Bearer header; the plugin does not run a token proxy.

After configuration, restart or reload Codex in the target repository and ask:

> Use Workilot, bind this repository, and show pending tasks.

For desktop Codex, the application process must inherit `WORKILOT_MCP_TOKEN`;
setting it in a separate terminal does not change an already running application.

## Bind a repository to a project

Each repository that uses Workilot stores a non-secret binding in `.workilot/project.toml`:

```toml
schema_version = 1
project_id = 7
project_key = "APP"
project_name = "Workilot"
```

Existing `.agentpilot/project.toml` bindings remain readable. New bindings are
written to `.workilot/project.toml`; an existing new binding always takes precedence.
If Codex already has an `agentpilot` remote connection, it can remain configured
with its original `AGENTPILOT_MCP_TOKEN` environment variable. When switching to
the new name, register `workilot` with `WORKILOT_MCP_TOKEN` and remove the old
registration after verifying the new one.

Call the local `workilot_project_binding` tool before project work, passing the absolute root of
the current repository as `project_root`. When the file is missing or
invalid, call the remote `list_projects`, ask the user to choose a project, then call the local
`workilot_bind_project` tool with `project_root` and the selected ID, key, and name. Never select the first project
implicitly. If the project is no longer authorized, stop and ask the user to bind again.

The plugin skills pass the bound `project_id` to every project-level tool call. `list_projects` is
the discovery exception. Item-specific calls are authorized by the item's real project and must
be checked against the repository binding before execution. The remote MCP server cannot read a
local repository file, so this binding check is a client workflow guard rather than a replacement
for Workilot's server-side authorization.

## Included skills

- `workilot-mcp`: route setup, diagnosis, project binding, and work execution.
- `workilot-mcp-setup`: configure the Codex Bearer MCP connection and bind a repository.
- `workilot-mcp-diagnose`: verify the remote connection and repository binding.
- `workilot-mcp-use`: execute work within the bound project.

The plugin contains only the local binding helper. Its launcher locates the installed plugin copy
under Codex's plugin cache, so startup does not depend on shell expansion or a machine-specific
absolute path. It never owns token storage: Codex manages the MCP connection and reads the token
from the configured environment variable. Workilot remains the authority for token validity,
Agent capabilities, API scopes, organization status, and project authorization.
