# Workilot MCP Plugin

This plugin connects Codex to Workilot through browser authorization and Codex's native Bearer MCP configuration, then binds each repository to one Workilot project.

## Install

```bash
codex plugin marketplace add starsarc/workilot-plugins
codex plugin add workilot-mcp@workilot
```

Requires Codex with plugin support, Git, and Python 3.10 or later. See the
[installation guide](../README.md#install-in-codex) for prerequisites and updates.

## Connect Workilot

In the target repository, ask Codex to initialize Workilot MCP. The plugin diagnoses the Codex
connection and repository binding, then repairs missing or expired authorization by opening
Workilot in your browser. Sign in, choose an organization, and approve operation scopes. The plugin verifies MCP
initialization and tool discovery, then writes the Bearer token to Codex's
`[mcp_servers.workilot]` HTTP authorization setting. The token is not written to a repository,
project binding, or chat.

The client authorization is shared across repositories in this Codex installation. Each repository
stores only its selected project in `.workilot/project.toml`. Old `.agentpilot` and `.taskwake`
bindings are reported as legacy and require a fresh project selection.

## Bind a repository to a project

Each repository that uses Workilot stores a non-secret binding in `.workilot/project.toml`:

```toml
schema_version = 1
project_id = 7
project_key = "APP"
project_name = "Workilot"
```

Call the local `workilot_project_binding` tool before project work, passing the absolute root of
the current repository as `project_root`. When the file is missing or invalid, call the remote
`list_projects`, ask the user to choose a project, then call `workilot_bind_project` with
`project_root` and the selected ID, key, and name. Never select the first project implicitly.

The plugin passes the bound `project_id` to every project-level tool call. The remote server
cannot read the local binding file, so this binding check complements Workilot's server-side
authorization; it does not replace it.

## Included skills

- `workilot-mcp`: route connection, diagnosis, project binding, and work execution.
- `workilot-mcp-setup`: perform browser authorization and configure the Codex Bearer connection.
- `workilot-mcp-diagnose`: verify the remote connection and repository binding.
- `workilot-mcp-use`: execute work within the bound project.

The local helper updates only Codex's Workilot MCP entry and never writes the credential to a
repository. Workilot remains the authority for token validity, organization status, operation
scopes, and project authorization.
