---
name: workilot-mcp-setup
description: Configure the Codex-native Workilot Bearer MCP connection and bind the current repository to one authorized project.
---

# Workilot MCP Setup

Workilot MCP is configured by Codex as a remote Streamable HTTP server. Register the deployed
`/mcp` endpoint with `codex mcp add workilot --url <endpoint> --bearer-token-env-var
WORKILOT_MCP_TOKEN`. Codex stores the endpoint URL literally and reads the Agent API key from
the named environment variable. Never put the token value in repository files, ordinary MCP
headers, or chat. The user creates or rotates the Agent API key in Workilot and makes it
available in the Codex process environment.

Do not call a plugin login, setup, or token-copy tool. Codex owns the Bearer connection. If the
remote MCP server is unavailable or unauthorized, explain which Codex MCP setting or Workilot
key scope needs attention.

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
first project implicitly. If the binding is outside the Agent's current scope, stop and ask the
user to bind again.

For every project-level MCP call, pass the bound `project_id`. The server requires a project
filter on reads and on every work-item-ID operation, then verifies the work item's actual project
matches the supplied ID and checks Agent scope, capability, and tool scope.
