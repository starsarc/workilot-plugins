---
name: workilot-mcp
description: Route Workilot MCP requests to Codex Bearer setup, connection diagnosis, repository project binding, or work-item execution.
---

# Workilot MCP

Use Codex's configured remote Workilot MCP tools. Read [setup](../workilot-mcp-setup/SKILL.md)
for the Bearer connection, [diagnose](../workilot-mcp-diagnose/SKILL.md) for connection
failures, and [use](../workilot-mcp-use/SKILL.md) for repository project binding and work.

Before any remote Workilot operation, call `workilot_connect` if the Codex-level connection is
missing or unauthorized. It handles browser approval and updates only Codex's Workilot MCP entry.
Never ask the user to run commands or copy the token.

Before any project operation, call `workilot_project_binding` with the current repository's
absolute root path as `project_root` to inspect `.workilot/project.toml`.
If it is missing, malformed, or identifies a project that is no longer authorized, stop and
guide the user through project discovery and binding. Never infer a project from the first
result and never issue an unfiltered cross-project query.

One Codex Bearer credential may access several projects authorized by the MCP Token. The repository
binding chooses exactly one project for this workspace. Pass its `project_id` to every
project-level and work-item-ID MCP tool. The
remote server cannot inspect the local binding file, so the skills enforce this client-side
binding selection, while Workilot verifies every supplied project against the target work item
and the MCP Token's project scope.
