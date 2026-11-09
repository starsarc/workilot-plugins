---
name: workilot-mcp-diagnose
description: Diagnose the Codex-managed Workilot Bearer MCP connection and current repository project binding without changing work items.
---

# Workilot MCP Diagnosis

Check the configured Workilot remote MCP server and call the local binding helper with the
current repository's absolute root path as `project_root`, then report:

1. The Codex MCP configuration points to the expected Workilot `/mcp` endpoint.
2. The `WORKILOT_MCP_TOKEN` variable is configured, without printing its value.
3. Remote MCP `initialize` and `tools/list` succeed.
4. `workilot_project_binding` reports a valid `.workilot/project.toml`.
5. `list_projects` succeeds and the bound project remains authorized.

Distinguish invalid, expired, or revoked tokens from missing API scopes, Agent capabilities, and
project permission errors. An empty authorized project directory can be valid; explain that the
Agent currently has no project access.

If the token is missing, expired, or revoked, direct the user to update the Codex environment
variable and restart or reload Codex as needed. Never print tokens or Authorization headers. Do
not replace an invalid repository binding with the first project in the list.
