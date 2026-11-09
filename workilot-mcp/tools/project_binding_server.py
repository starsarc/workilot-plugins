#!/usr/bin/env python3
"""MCP stdio tools for the non-secret Workilot repository binding.

The Workilot connection itself is configured by Codex as a remote Streamable HTTP
server. This small local server only reads and writes ``.workilot/project.toml``;
it never receives, stores, or forwards the Bearer token.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any


VERSION = "0.4.0"
SUPPORTED_PROTOCOL_VERSIONS = {"2025-03-26", "2025-06-18", "2025-11-25"}
ROOT_ENV = "WORKILOT_PROJECT_ROOT"
CONFIG_RELATIVE_PATH = Path(".workilot") / "project.toml"
_KEY_RE = re.compile(r"^(schema_version|project_id|project_key|project_name)\s*=\s*(.+?)\s*$")


class BindingError(Exception):
    """Raised for invalid binding input or an invalid on-disk binding."""


def project_root(configured: Any = None) -> Path:
    explicit = str(configured or "").strip()
    if explicit:
        root = Path(explicit).expanduser()
    else:
        configured = (os.environ.get(ROOT_ENV) or os.environ.get("TASKWAKE_PROJECT_ROOT") or os.environ.get("AGENTPILOT_PROJECT_ROOT", "")).strip()
        root = Path(configured).expanduser() if configured else Path.cwd()
    if not root.is_absolute():
        raise BindingError("project_root must be an absolute path")
    root = root.resolve()
    if not root.is_dir():
        raise BindingError("project_root must be an existing directory")
    return root


def binding_path(root: Any = None) -> Path:
    return project_root(root) / CONFIG_RELATIVE_PATH


def _parse_scalar(raw: str, field: str) -> int | str:
    if field in {"schema_version", "project_id"}:
        try:
            return int(raw)
        except ValueError as exc:
            raise BindingError(f"{field} must be an integer") from exc
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise BindingError(f"{field} must be a quoted string") from exc
    if not isinstance(value, str) or not value.strip():
        raise BindingError(f"{field} must be a non-empty string")
    return value.strip()


def read_binding(root: Any = None) -> dict[str, Any]:
    path = binding_path(root)
    if not path.exists():
        for folder in (".taskwake", ".agentpilot"):
            legacy_path = project_root(root) / folder / "project.toml"
            if legacy_path.exists():
                path = legacy_path
                break
    if not path.exists():
        return {"status": "missing", "path": str(path)}
    if not path.is_file():
        return {"status": "invalid", "path": str(path), "error": "project binding path is not a file"}

    values: dict[str, Any] = {}
    try:
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            match = _KEY_RE.match(line)
            if not match:
                raise BindingError(f"unsupported or malformed setting on line {line_number}")
            field, raw = match.groups()
            if field in values:
                raise BindingError(f"duplicate setting: {field}")
            values[field] = _parse_scalar(raw, field)
        schema_version = values.get("schema_version")
        if schema_version != 1:
            raise BindingError("schema_version must be 1")
        project_id = values.get("project_id")
        if not isinstance(project_id, int) or project_id <= 0:
            raise BindingError("project_id must be positive")
        for field in ("project_key", "project_name"):
            if field not in values:
                raise BindingError(f"{field} is required")
    except (OSError, UnicodeError, BindingError) as exc:
        return {"status": "invalid", "path": str(path), "error": str(exc)}

    return {
        "status": "bound",
        "path": str(path),
        "project": {
            "id": values["project_id"],
            "key": values["project_key"],
            "name": values["project_name"],
        },
    }


def _string_argument(arguments: dict[str, Any], field: str) -> str:
    value = str(arguments.get(field) or "").strip()
    if not value:
        raise BindingError(f"{field} is required")
    return value


def bind_project(arguments: dict[str, Any]) -> dict[str, Any]:
    raw_id = arguments.get("project_id")
    try:
        project_id = int(raw_id)
    except (TypeError, ValueError) as exc:
        raise BindingError("project_id must be an integer") from exc
    if project_id <= 0:
        raise BindingError("project_id must be positive")
    project_key = _string_argument(arguments, "project_key")
    project_name = _string_argument(arguments, "project_name")

    path = binding_path(arguments.get("project_root"))
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.parent.chmod(0o700)
    except OSError:
        pass
    contents = "\n".join(
        [
            "# Workilot repository binding; contains no credentials.",
            "schema_version = 1",
            f"project_id = {project_id}",
            f"project_key = {json.dumps(project_key, ensure_ascii=False)}",
            f"project_name = {json.dumps(project_name, ensure_ascii=False)}",
            "",
        ]
    )
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
            handle.write(contents)
            temporary = Path(handle.name)
        try:
            temporary.chmod(0o600)
        except OSError:
            pass
        os.replace(temporary, path)
    except OSError as exc:
        try:
            temporary.unlink(missing_ok=True)
        except (OSError, UnboundLocalError):
            pass
        raise BindingError(f"cannot write project binding: {exc}") from exc

    return read_binding(arguments.get("project_root"))


TOOLS = [
    {
        "name": "workilot_project_binding",
        "description": "Read and validate the current repository's Workilot project binding. Pass its absolute project_root.",
        "inputSchema": {
            "type": "object",
            "required": ["project_root"],
            "properties": {"project_root": {"type": "string", "description": "Absolute path to the current repository root."}},
        },
    },
    {
        "name": "workilot_bind_project",
        "description": "Write the selected non-secret Workilot project binding for this repository after list_projects confirmation.",
        "inputSchema": {
            "type": "object",
            "required": ["project_root", "project_id", "project_key", "project_name"],
            "properties": {
                "project_root": {"type": "string", "description": "Absolute path to the current repository root."},
                "project_id": {"type": "integer"},
                "project_key": {"type": "string"},
                "project_name": {"type": "string"},
            },
        },
    },
]


def result(value: Any) -> dict[str, Any]:
    encoded = json.dumps(value, ensure_ascii=False)
    return {"content": [{"type": "text", "text": encoded}], "structuredContent": value}


def dispatch(method: str, params: dict[str, Any]) -> dict[str, Any] | None:
    if method == "notifications/initialized":
        return None
    if method == "initialize":
        requested_version = params.get("protocolVersion")
        if requested_version not in SUPPORTED_PROTOCOL_VERSIONS:
            raise BindingError(f"unsupported MCP protocol version: {requested_version}")
        return {
            "protocolVersion": requested_version,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "workilot-project-binding", "version": VERSION},
        }
    if method == "tools/list":
        return {"tools": TOOLS}
    if method != "tools/call":
        raise BindingError(f"unsupported MCP method: {method}")
    name = str(params.get("name") or "")
    arguments = params.get("arguments") or {}
    if not isinstance(arguments, dict):
        raise BindingError("arguments must be an object")
    if name == "workilot_project_binding":
        if not str(arguments.get("project_root") or "").strip():
            raise BindingError("project_root is required")
        return result(read_binding(arguments.get("project_root")))
    if name == "workilot_bind_project":
        if not str(arguments.get("project_root") or "").strip():
            raise BindingError("project_root is required")
        return result(bind_project(arguments))
    raise BindingError(f"unknown local tool: {name}")


def serve() -> None:
    for line in os.sys.stdin:
        if not line.strip():
            continue
        request_id: Any = None
        try:
            request = json.loads(line)
            request_id = request.get("id")
            value = dispatch(str(request.get("method") or ""), request.get("params") or {})
            if request_id is not None and value is not None:
                print(json.dumps({"jsonrpc": "2.0", "id": request_id, "result": value}, ensure_ascii=False), flush=True)
        except Exception as exc:
            if request_id is not None:
                print(json.dumps({"jsonrpc": "2.0", "id": request_id, "error": {"code": -32000, "message": str(exc)}}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    serve()
