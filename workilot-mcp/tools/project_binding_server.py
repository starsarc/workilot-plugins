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
import time
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path
from typing import Any


VERSION = "0.5.0"
SUPPORTED_PROTOCOL_VERSIONS = {"2025-03-26", "2025-06-18", "2025-11-25"}
ROOT_ENV = "WORKILOT_PROJECT_ROOT"
WORKILOT_URL = os.environ.get("WORKILOT_URL", "https://pilot.yoron.cc").rstrip("/")
CONFIG_RELATIVE_PATH = Path(".workilot") / "project.toml"
_KEY_RE = re.compile(r"^(schema_version|project_id|project_key|project_name)\s*=\s*(.+?)\s*$")


class BindingError(Exception):
    """Raised for invalid binding input or an invalid on-disk binding."""


class MCPUnauthorized(BindingError):
    """Raised only when the remote MCP endpoint rejects the Bearer token."""


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


def _http_json(url: str, *, method: str = "GET", body: dict[str, Any] | None = None, token: str = "") -> dict[str, Any]:
    payload = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Accept": "application/json"}
    if payload is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, data=payload, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8")) if response.status != 204 else {}
    except urllib.error.HTTPError as exc:
        if exc.code in {400, 401, 403}:
            raise BindingError("Workilot rejected the authorization or MCP token. Restart the connection flow and check the approved account.") from exc
        raise BindingError(f"Workilot request failed with HTTP {exc.code}") from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise BindingError("Could not reach Workilot. Check the network and try the connection again.") from exc


def codex_config_path() -> Path:
    home = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex").expanduser()
    return home / "config.toml"


def read_codex_workilot_entry() -> dict[str, str]:
    path = codex_config_path()
    if not path.exists():
        return {}
    lines = path.read_text(encoding="utf-8").splitlines()
    in_section = False
    entry: dict[str, str] = {}
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            in_section = stripped == "[mcp_servers.workilot]"
            continue
        if in_section:
            match = re.match(r'^(url|http_headers|bearer_token_env_var)\s*=\s*(.*)$', stripped)
            if match:
                entry[match.group(1)] = match.group(2)
    return entry


def configure_codex_mcp(token: str) -> None:
    if not token.startswith("wl_mcp_"):
        raise BindingError("Workilot returned an invalid MCP token; the Codex configuration was not changed.")
    path = codex_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    old = path.read_text(encoding="utf-8") if path.exists() else ""
    lines = old.splitlines()
    section_start = None
    section_end = len(lines)
    preserved_headers: dict[str, str] = {}
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped == "[mcp_servers.workilot]":
            section_start = index
            for next_index in range(index + 1, len(lines)):
                candidate = lines[next_index].strip()
                if candidate.startswith("[") and candidate.endswith("]") and not candidate.startswith("[mcp_servers.workilot."):
                    section_end = next_index
                    break
            break
    if section_start is None:
        section = ["[mcp_servers.workilot]", f"url = {json.dumps(WORKILOT_URL + '/mcp')}"]
        lines.extend([""] if lines and lines[-1].strip() else [])
        lines.extend(section)
        section_start = len(lines) - len(section)
        section_end = len(lines)
    else:
        index = section_start + 1
        while index < section_end:
            stripped = lines[index].strip()
            if re.match(r"^(url|http_headers|bearer_token_env_var)\s*=", stripped):
                if stripped.startswith("http_headers"):
                    for quoted_key, bare_key, value in re.findall(
                        r'(?:(?:"((?:[^"\\]|\\.)+)")|([A-Za-z0-9_-]+))\s*=\s*"((?:[^"\\]|\\.)*)"',
                        stripped,
                    ):
                        key = json.loads('"' + quoted_key + '"') if quoted_key else bare_key
                        if key.lower() != "authorization":
                            preserved_headers[key] = json.loads('"' + value + '"')
                lines.pop(index)
                section_end -= 1
                continue
            if stripped == "[mcp_servers.workilot.http_headers]":
                end = index + 1
                while end < len(lines) and not lines[end].lstrip().startswith("["):
                    match = re.match(
                        r'^\s*(?:(?:"((?:[^"\\]|\\.)+)")|([A-Za-z0-9_-]+))\s*=\s*"((?:[^"\\]|\\.)*)"\s*$',
                        lines[end],
                    )
                    if match:
                        key = json.loads('"' + match.group(1) + '"') if match.group(1) else match.group(2)
                        if key.lower() != "authorization":
                            preserved_headers[key] = json.loads('"' + match.group(3) + '"')
                    end += 1
                del lines[index:end]
                section_end -= end - index
                continue
            index += 1
        url_line = f"url = {json.dumps(WORKILOT_URL + '/mcp')}"
        url_index = next((i for i in range(section_start + 1, section_end) if lines[i].strip().startswith("url =")), None)
        if url_index is None:
            lines.insert(section_start + 1, url_line)
            section_end += 1
        else:
            lines[url_index] = url_line
    preserved_headers["Authorization"] = "Bearer " + token
    encoded_headers = ", ".join(f'{json.dumps(key)} = {json.dumps(value)}' for key, value in preserved_headers.items())
    header_line = f"http_headers = {{ {encoded_headers} }}"
    url_index = next((i for i in range(section_start + 1, section_end) if lines[i].strip().startswith("url =")), section_start)
    lines.insert(url_index + 1, header_line)
    content = "\n".join(lines).rstrip() + "\n"
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
            handle.write(content)
            temporary = Path(handle.name)
        temporary.chmod(0o600)
        os.replace(temporary, path)
        path.chmod(0o600)
    except OSError as exc:
        if temporary:
            temporary.unlink(missing_ok=True)
        raise BindingError("Could not update Codex MCP settings. The Workilot token was not saved.") from exc


def verify_remote_mcp(token: str) -> None:
    def send(payload: dict[str, Any]) -> tuple[dict[str, Any], str]:
        request = urllib.request.Request(
            WORKILOT_URL + "/mcp",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                body = response.read().decode("utf-8")
                content_type = response.headers.get("Content-Type", "")
        except urllib.error.HTTPError as exc:
            if exc.code in {401, 403}:
                raise MCPUnauthorized("Workilot rejected the MCP token. Review the authorization and try again.") from exc
            raise BindingError(f"Workilot MCP request failed with HTTP {exc.code}.") from exc
        if "text/event-stream" in content_type:
            data = next((line[6:].strip() for line in body.splitlines() if line.startswith("data: ")), "")
        else:
            data = body
        try:
            return json.loads(data) if data else {}, content_type
        except json.JSONDecodeError as exc:
            raise BindingError("Workilot returned an invalid MCP response.") from exc

    initialize = {
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {"protocolVersion": "2025-11-25", "capabilities": {}, "clientInfo": {"name": "workilot-codex-plugin", "version": VERSION}},
    }
    response, _ = send(initialize)
    if not response.get("result", {}).get("serverInfo"):
        raise BindingError("Workilot did not complete MCP initialization.")
    send({"jsonrpc": "2.0", "method": "notifications/initialized"})
    tools, _ = send({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
    if not isinstance(tools.get("result", {}).get("tools"), list):
        raise BindingError("Workilot responded, but MCP tool discovery did not succeed.")


def connect_workilot() -> dict[str, Any]:
    current = read_codex_workilot_entry()
    existing_token = ""
    if current.get("url", "").strip('"') == WORKILOT_URL + "/mcp":
        match = re.search(r'(?:(?:"Authorization")|Authorization)\s*=\s*"Bearer\s+(wl_mcp_[^"\\]+)"', current.get("http_headers", ""))
        existing_token = match.group(1) if match else ""
        if existing_token:
            try:
                verify_remote_mcp(existing_token)
                return {"status": "configured", "server": "workilot", "url": WORKILOT_URL + "/mcp", "message": "Workilot is connected through Codex MCP settings."}
            except MCPUnauthorized:
                pass
    created = _http_json(WORKILOT_URL + "/api/mcp/device-authorizations", method="POST", body={})
    item = created.get("item", {})
    device_code = created.get("device_code", "")
    user_code = item.get("user_code", "")
    verification_uri = item.get("verification_uri", "")
    if not device_code or not user_code or not verification_uri:
        raise BindingError("Workilot returned an incomplete authorization request.")
    authorization_url = verification_uri + "?user_code=" + urllib.parse.quote(user_code)
    webbrowser.open(authorization_url)
    expires_at = item.get("expires_at", "")
    expiry = time.time() + 600
    if expires_at:
        try:
            from datetime import datetime
            expiry = datetime.fromisoformat(expires_at.replace("Z", "+00:00")).timestamp()
        except ValueError:
            pass
    interval = max(2, int(item.get("interval", 3)))
    while time.time() < expiry:
        result = _http_json(WORKILOT_URL + "/api/mcp/device-authorizations/status", method="POST", body={"device_code": device_code})
        status = result.get("item", {}).get("status")
        if status == "authorized":
            token = result.get("token", "")
            verify_remote_mcp(token)
            configure_codex_mcp(token)
            return {"status":"connected","server":"workilot","url":WORKILOT_URL+"/mcp","organization_id":result.get("item",{}).get("organization_id"),"next_step":"Bind this repository to one authorized project before project operations."}
        if status in {"denied", "expired", "consumed"}:
            raise BindingError("Workilot authorization was denied or expired. Start the connection flow again.")
        time.sleep(interval)
    raise BindingError("Workilot authorization timed out. Start the connection flow again.")


TOOLS = [
    {
        "name": "workilot_connect",
        "description": "Connect this Codex installation to Workilot. Opens the Workilot login and approval page, waits for authorization, verifies MCP access, and stores the Bearer token in Codex's MCP configuration (never in a repository).",
        "inputSchema": {"type": "object", "properties": {}},
    },
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
    if name == "workilot_connect":
        return result(connect_workilot())
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
