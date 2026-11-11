---
name: workilot-mcp
description: Route Workilot MCP requests to Codex Bearer setup, connection diagnosis, repository project binding, or work-item execution.
---

# Workilot MCP

Use Codex's configured remote Workilot MCP tools. Read [setup](../workilot-mcp-setup/SKILL.md)
for the complete initialization flow, [diagnose](../workilot-mcp-diagnose/SKILL.md) for
connection failures, and [use](../workilot-mcp-use/SKILL.md) for repository project binding and
work.

When the user asks to initialize, connect, configure, set up, or use Workilot, own the entire
setup flow. First call `workilot_diagnose` with the current repository's absolute root. Based on
its status, call `workilot_connect` for a missing, misconfigured, missing-authorization, or
unauthorized connection. It opens the browser and waits for sign-in and approval; never ask the
user to run commands, copy a token, or manually edit Codex configuration. If authorization
succeeds but the current session cannot see the newly configured remote tools, tell the user to
reload the Codex session and then continue the diagnosis automatically after reload.

Do not stop after connection setup. Once the Codex connection is healthy, continue with the
repository binding check below. If the user is not authenticated in the browser, explicitly tell
them that the opened Workilot login page is the only required user action, then keep waiting for
the authorization result.

Before any project operation, call `workilot_project_binding` with the current repository's
absolute root path as `project_root` to inspect `.workilot/project.toml`.
If it is missing, malformed, reports `legacy`, or identifies a project that is no longer
authorized, call `list_projects` and present the authorized projects by name, key, and ID. Ask the
user to choose one, then call `workilot_bind_project` with the exact selected identity. Never infer
a project from the first result and never issue an unfiltered cross-project query. If the list is
empty, explain that the connection works but its MCP Token has no project access; guide the user to
have an organization administrator update that token's project permissions before retrying.

One Codex Bearer credential may access several projects authorized by the MCP Token. The repository
binding chooses exactly one project for this workspace. Pass its `project_id` to every
project-level and work-item-ID MCP tool. The
remote server cannot inspect the local binding file, so the skills enforce this client-side
binding selection, while Workilot verifies every supplied project against the target work item
and the MCP Token's project scope.
