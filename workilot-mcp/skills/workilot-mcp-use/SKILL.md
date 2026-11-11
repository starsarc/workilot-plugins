---
name: workilot-mcp-use
description: Find, inspect, create, claim, comment on, and complete Workilot work items within the current repository's bound project.
---

# Workilot MCP Use

Call the local `workilot_project_binding` tool before using project tools, passing the absolute
root path of the current repository as `project_root`. It must report a valid
`.workilot/project.toml` with a `project_id`. If it is missing or invalid, call `list_projects`,
ask the user which project to bind, and call `workilot_bind_project` with `project_root` and the exact returned
identity. Do not choose the first result automatically. If the bound project is unavailable, stop
and rebind instead of switching projects silently.

Pass the bound `project_id` to every project-level and item-ID tool, including `get_work_item`,
`claim_work_item`, comments, run lifecycle, status, result, and confirmation tools. Never omit it.
The server verifies that an item's actual project matches the supplied project ID.

The project filter narrows the MCP Token's authorization and cannot grant access to a project. If
the server rejects the bound project, stop and help the user rebind or request Token project scope changes.

For execution, check `list_my_runs`, discover ready work with `list_agent_tasks`, inspect with
`get_work_item`, and claim when the user's request authorizes execution. Existing authorization
in the conversation is sufficient; do not ask again merely because the next step writes data.
Record useful progress, call `heartbeat_agent_run` during sustained active work, and finish with
`submit_agent_run` or release unfinished work with `release_work_item`. Use
`request_human_confirmation` for a decision that needs the user.

Discovery alone does not authorize claiming or closing work. Treat an out-of-scope response as
an error and stop; diagnose without silently changing the repository binding.
