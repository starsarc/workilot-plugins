import importlib.util
import os
import tempfile
import tomllib
import unittest
from unittest.mock import patch
from pathlib import Path


SCRIPT = Path(__file__).with_name("project_binding_server.py")
SPEC = importlib.util.spec_from_file_location("project_binding_server", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class ProjectBindingTests(unittest.TestCase):
    def test_previous_product_binding_requires_explicit_reselection(self):
        with tempfile.TemporaryDirectory() as directory:
            previous = Path(directory) / ".agentpilot" / "project.toml"
            previous.parent.mkdir()
            previous.write_text('schema_version = 1\nproject_id = 7\nproject_key = "OLD"\nproject_name = "Existing project"\n')
            result = MODULE.read_binding(directory)
            self.assertEqual(result["status"], "legacy")
            self.assertEqual(result["path"], str(previous.resolve()))
            result = MODULE.bind_project({"project_root": directory, "project_id": 8, "project_key": "NEW", "project_name": "Workilot"})
            self.assertEqual(result["project"]["id"], 8)
            self.assertEqual(Path(result["path"]), Path(directory).resolve() / ".workilot" / "project.toml")
            self.assertIn('project_id = 7', previous.read_text())

    def test_taskwake_binding_requires_explicit_reselection(self):
        with tempfile.TemporaryDirectory() as directory:
            previous = Path(directory) / ".taskwake" / "project.toml"
            previous.parent.mkdir()
            previous.write_text('schema_version = 1\nproject_id = 9\nproject_key = "OLD"\nproject_name = "Previous product"\n')
            result = MODULE.read_binding(directory)
            self.assertEqual(result["status"], "legacy")
            self.assertEqual(result["path"], str(previous.resolve()))
            result = MODULE.bind_project({"project_root": directory, "project_id": 10, "project_key": "NEW", "project_name": "Workilot"})
            self.assertEqual(Path(result["path"]), Path(directory).resolve() / ".workilot" / "project.toml")

    def test_invalid_new_binding_does_not_fall_back_to_previous_project(self):
        with tempfile.TemporaryDirectory() as directory:
            for folder in (".workilot", ".agentpilot"):
                path = Path(directory) / folder
                path.mkdir()
                (path / "project.toml").write_text('schema_version = 1\nproject_id = 7\nproject_key = "APP"\nproject_name = "Workilot"\n')
            (Path(directory).resolve() / ".workilot" / "project.toml").write_text("invalid binding")
            self.assertEqual(MODULE.read_binding(directory)["status"], "invalid")

    def test_missing_binding_is_reported_without_creating_files(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch_env(MODULE.ROOT_ENV, directory):
                result = MODULE.read_binding()
            self.assertEqual(result["status"], "missing")
            self.assertFalse((Path(directory) / ".workilot").exists())

    def test_bind_and_read_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            result = MODULE.bind_project({"project_root": directory, "project_id": 7, "project_key": "APP", "project_name": "Workilot"})
            self.assertEqual(result["status"], "bound")
            self.assertEqual(result["project"], {"id": 7, "key": "APP", "name": "Workilot"})
            on_disk = Path(directory) / ".workilot" / "project.toml"
            self.assertEqual(MODULE.read_binding(directory), result)
            self.assertNotIn("token", on_disk.read_text())

    def test_invalid_binding_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".workilot"
            path.mkdir()
            (path / "project.toml").write_text("schema_version = 1\nproject_id = 0\n", encoding="utf-8")
            with patch_env(MODULE.ROOT_ENV, directory):
                result = MODULE.read_binding(directory)
            self.assertEqual(result["status"], "invalid")
            self.assertIn("project_id", result["error"])

    def test_bind_requires_complete_project_identity(self):
        with self.assertRaises(MODULE.BindingError):
            MODULE.bind_project({"project_root": "/tmp/repo", "project_id": 7, "project_key": "APP"})

    def test_dispatch_exposes_connection_and_binding_tools(self):
        response = MODULE.dispatch("tools/list", {})
        self.assertEqual([item["name"] for item in response["tools"]], [
            "workilot_diagnose",
            "workilot_connect",
            "workilot_project_binding",
            "workilot_bind_project",
        ])

    def test_connection_status_reports_missing_connection_and_action(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch_env("CODEX_HOME", directory):
                result = MODULE.connection_status(directory)
        self.assertEqual(result["status"], "missing")
        self.assertEqual(result["next_step"], "call workilot_connect")
        self.assertFalse(result["authorization_present"])

    def test_connection_status_reports_connected_but_missing_binding(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "config.toml"
            config.write_text(
                '[mcp_servers.workilot]\n'
                f'url = "{MODULE.WORKILOT_URL}/mcp"\n'
                'http_headers = { "Authorization" = "Bearer wl_mcp_test" }\n',
                encoding="utf-8",
            )
            with patch_env("CODEX_HOME", directory), patch.object(MODULE, "verify_remote_mcp"):
                result = MODULE.connection_status(directory)
        self.assertEqual(result["status"], "connected")
        self.assertEqual(result["binding"]["status"], "missing")
        self.assertIn("list_projects", result["next_step"])

    def test_connection_status_recognizes_authorization_in_nested_headers(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "config.toml"
            config.write_text(
                '[mcp_servers.workilot]\n'
                f'url = "{MODULE.WORKILOT_URL}/mcp"\n'
                '\n'
                '[mcp_servers.workilot.http_headers]\n'
                'authorization = "Bearer wl_mcp_test"\n',
                encoding="utf-8",
            )
            with patch_env("CODEX_HOME", directory), patch.object(MODULE, "verify_remote_mcp") as verify:
                result = MODULE.connection_status(directory)
        self.assertEqual(result["status"], "connected")
        self.assertTrue(result["authorization_present"])
        verify.assert_called_once_with("wl_mcp_test")
        self.assertNotIn("wl_mcp_test", str(result))

    def test_initialize_negotiates_requested_protocol_version(self):
        for version in ("2025-03-26", "2025-06-18", "2025-11-25"):
            with self.subTest(version=version):
                response = MODULE.dispatch("initialize", {"protocolVersion": version})
                self.assertEqual(response["protocolVersion"], version)

    def test_initialize_rejects_unknown_protocol_version(self):
        with self.assertRaisesRegex(MODULE.BindingError, "unsupported MCP protocol version"):
            MODULE.dispatch("initialize", {"protocolVersion": "2099-01-01"})

    def test_binding_tools_require_repository_root(self):
        response = MODULE.dispatch("tools/list", {})
        for tool in response["tools"]:
            if tool["name"] == "workilot_connect":
                continue
            self.assertIn("project_root", tool["inputSchema"]["required"])

    def test_codex_connection_is_written_to_native_config_without_touching_other_servers(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            config = home / "config.toml"
            config.write_text('[mcp_servers.other]\nurl = "https://other.example/mcp"\n\n[mcp_servers.workilot]\nurl = "https://old.example/mcp"\nbearer_token_env_var = "OLD_TOKEN"\n\n[mcp_servers.workilot.http_headers]\nX-Other = "keep"\n', encoding="utf-8")
            with patch_env("CODEX_HOME", directory):
                MODULE.configure_codex_mcp("wl_mcp_test-token")
            parsed = tomllib.loads(config.read_text(encoding="utf-8"))
            self.assertEqual(parsed["mcp_servers"]["other"]["url"], "https://other.example/mcp")
            workilot = parsed["mcp_servers"]["workilot"]
            self.assertEqual(workilot["url"], MODULE.WORKILOT_URL + "/mcp")
            self.assertEqual(workilot["http_headers"]["Authorization"], "Bearer wl_mcp_test-token")
            self.assertEqual(workilot["http_headers"]["X-Other"], "keep")
            self.assertNotIn("bearer_token_env_var", workilot)
            self.assertEqual(Path(config).stat().st_mode & 0o777, 0o600)

    def test_codex_connection_writes_authorization_at_workilot_root_with_nested_headers(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "config.toml"
            config.write_text(
                '[mcp_servers.workilot]\n'
                'url = "https://old.example/mcp"\n'
                '\n'
                '[mcp_servers.workilot.http_headers]\n'
                'X-Other = "keep"\n'
                '\n'
                '[projects."/tmp/example"]\n'
                'trust_level = "trusted"\n',
                encoding="utf-8",
            )
            with patch_env("CODEX_HOME", directory):
                MODULE.configure_codex_mcp("wl_mcp_test-token")
            parsed = tomllib.loads(config.read_text(encoding="utf-8"))
            workilot = parsed["mcp_servers"]["workilot"]
            self.assertEqual(workilot["http_headers"]["Authorization"], "Bearer wl_mcp_test-token")
            self.assertEqual(workilot["http_headers"]["X-Other"], "keep")
            self.assertEqual(parsed["projects"]["/tmp/example"]["trust_level"], "trusted")

    def test_codex_config_header_insertion_does_not_put_token_under_nested_table(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "config.toml"
            config.write_text(
                '[mcp_servers.workilot]\n'
                'url = "https://old.example/mcp"\n'
                '\n'
                '[mcp_servers.workilot.experimental]\n'
                'enabled = true\n',
                encoding="utf-8",
            )
            with patch_env("CODEX_HOME", directory):
                MODULE.configure_codex_mcp("wl_mcp_test-token")
            parsed = tomllib.loads(config.read_text(encoding="utf-8"))
            self.assertEqual(parsed["mcp_servers"]["workilot"]["http_headers"]["Authorization"], "Bearer wl_mcp_test-token")
            self.assertTrue(parsed["mcp_servers"]["workilot"]["experimental"]["enabled"])

    def test_reconfiguring_codex_preserves_quoted_custom_headers(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "config.toml"
            config.write_text(
                '[mcp_servers.workilot]\n'
                'url = "https://old.example/mcp"\n'
                'http_headers = { "X-Client-Name" = "Codex Desktop", "Authorization" = "Bearer wl_mcp_old" }\n',
                encoding="utf-8",
            )
            with patch_env("CODEX_HOME", directory):
                MODULE.configure_codex_mcp("wl_mcp_new-token")
            parsed = tomllib.loads(config.read_text(encoding="utf-8"))
            headers = parsed["mcp_servers"]["workilot"]["http_headers"]
            self.assertEqual(headers["X-Client-Name"], "Codex Desktop")
            self.assertEqual(headers["Authorization"], "Bearer wl_mcp_new-token")

    def test_codex_connection_rejects_invalid_token_without_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch_env("CODEX_HOME", directory):
                with self.assertRaisesRegex(MODULE.BindingError, "invalid MCP token"):
                    MODULE.configure_codex_mcp("not-a-token")
                self.assertFalse((Path(directory) / "config.toml").exists())

    def test_project_binding_file_never_contains_mcp_token(self):
        with tempfile.TemporaryDirectory() as directory:
            MODULE.bind_project({"project_root": directory, "project_id": 8, "project_key": "APP", "project_name": "Example"})
            contents = (Path(directory) / ".workilot" / "project.toml").read_text(encoding="utf-8")
            self.assertNotIn("wl_mcp_", contents)

    def test_remote_auth_failure_has_specific_error_type(self):
        error = MODULE.MCPUnauthorized("rejected")
        self.assertIsInstance(error, MODULE.BindingError)

    def test_existing_token_is_not_replaced_on_remote_server_error(self):
        with patch.object(MODULE, "read_codex_workilot_entry", return_value={
            "url": f'"{MODULE.WORKILOT_URL}/mcp"',
            "http_headers": '{ "Authorization" = "Bearer wl_mcp_current" }',
        }), patch.object(MODULE, "verify_remote_mcp", side_effect=MODULE.BindingError("HTTP 503")), patch.object(MODULE, "_http_json") as request:
            with self.assertRaisesRegex(MODULE.BindingError, "HTTP 503"):
                MODULE.connect_workilot()
            request.assert_not_called()

    def test_existing_token_reauthorization_only_follows_auth_rejection(self):
        created = {
            "item": {
                "user_code": "ABCD2345",
                "verification_uri": "https://pilot.example/mcp/authorize",
                "expires_at": "2099-01-01T00:00:00Z",
                "interval": 2,
            },
            "device_code": "short-lived-code",
        }
        approved = {"item": {"status": "authorized", "organization_id": 12}, "token": "wl_mcp_reauthorized"}
        with patch.object(MODULE, "read_codex_workilot_entry", return_value={
            "url": f'"{MODULE.WORKILOT_URL}/mcp"',
            "http_headers": '{ "Authorization" = "Bearer wl_mcp_expired" }',
        }), patch.object(MODULE, "verify_remote_mcp", side_effect=[MODULE.MCPUnauthorized("expired"), None]), patch.object(
            MODULE, "_http_json", side_effect=[created, approved]
        ) as request, patch.object(MODULE.webbrowser, "open", return_value=True), patch.object(
            MODULE, "configure_codex_mcp"
        ) as configure:
            result = MODULE.connect_workilot()
        self.assertEqual(result["status"], "connected")
        self.assertEqual(request.call_args_list[1].kwargs["body"], {"device_code": "short-lived-code"})
        configure.assert_called_once_with("wl_mcp_reauthorized")


class patch_env:
    def __init__(self, name, value):
        self.name = name
        self.value = value
        self.old = None

    def __enter__(self):
        self.old = os.environ.get(self.name)
        os.environ[self.name] = self.value

    def __exit__(self, *_):
        if self.old is None:
            os.environ.pop(self.name, None)
        else:
            os.environ[self.name] = self.old


if __name__ == "__main__":
    unittest.main()
