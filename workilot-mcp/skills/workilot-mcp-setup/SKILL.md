---
name: workilot-mcp-setup
description: Configure the Codex-native Workilot Bearer MCP connection and bind the current repository to one authorized project.
---

# Workilot MCP Setup

Workilot MCP is configured as Codex's remote Streamable HTTP server. Start by calling the local
`workilot_diagnose` tool with the current repository root. It detects missing configuration,
wrong endpoint, missing authorization, expired/revoked authorization, and an unreachable server.
For the first four recoverable states, call `workilot_connect`. It opens Workilot in the browser,
waits for the user to sign in and approve an organization and operation scopes, verifies MCP
initialization and tool discovery, then writes the returned Bearer token into Codex's
`[mcp_servers.workilot]` HTTP authorization setting. Never show or log the token. Never write it
into a repository, a project binding, or chat. The token is client-level and shared by
repositories using this Codex install.

If the configuration is updated but the remote tools are not visible to the current Codex session,
reload the Codex session once. This is a client refresh, not a user configuration step; do not ask
the user to run setup commands or copy the token. After reload, diagnose again and continue setup.

Before project work, call `workilot_project_binding` from the local binding server with the
absolute root path of the current repository as `project_root`. It reads
`.workilot/project.toml`, which contains only non-secret binding metadata:

```toml
schema_version = 1
project_id = 7
project_key = "APP"
project_name = "Workilot"
```

If it is missing or invalid, call the remote `list_projects`, ask the user to select a project,
then call `workilot_bind_project` with `project_root` and the exact returned ID, key, and name. Do not select the
first project implicitly. If the binding is outside the MCP Token's current scope, stop and ask the
user to bind again.

For every project-level MCP call, pass the bound `project_id`. The server requires a project
filter on reads and on every work-item-ID operation, then verifies the work item's actual project
matches the supplied ID and checks Token project scope and operation scopes.
