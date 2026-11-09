import importlib.util
import os
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("project_binding_server.py")
SPEC = importlib.util.spec_from_file_location("project_binding_server", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class ProjectBindingTests(unittest.TestCase):
    def test_reads_previous_binding_but_writes_new_binding(self):
        with tempfile.TemporaryDirectory() as directory:
            previous = Path(directory) / ".agentpilot" / "project.toml"
            previous.parent.mkdir()
            previous.write_text('schema_version = 1\nproject_id = 7\nproject_key = "OLD"\nproject_name = "Existing project"\n')
            result = MODULE.read_binding(directory)
            self.assertEqual(result["project"]["id"], 7)
            self.assertEqual(result["path"], str(previous.resolve()))
            result = MODULE.bind_project({"project_root": directory, "project_id": 8, "project_key": "NEW", "project_name": "Workilot"})
            self.assertEqual(result["project"]["id"], 8)
            self.assertEqual(Path(result["path"]), Path(directory).resolve() / ".workilot" / "project.toml")
            self.assertIn('project_id = 7', previous.read_text())

    def test_reads_taskwake_binding_and_writes_workilot_path(self):
        with tempfile.TemporaryDirectory() as directory:
            previous = Path(directory) / ".taskwake" / "project.toml"
            previous.parent.mkdir()
            previous.write_text('schema_version = 1\nproject_id = 9\nproject_key = "OLD"\nproject_name = "Previous product"\n')
            result = MODULE.read_binding(directory)
            self.assertEqual(result["project"]["id"], 9)
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

    def test_dispatch_exposes_only_binding_tools(self):
        response = MODULE.dispatch("tools/list", {})
        self.assertEqual([item["name"] for item in response["tools"]], [
            "workilot_project_binding",
            "workilot_bind_project",
        ])

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
            self.assertIn("project_root", tool["inputSchema"]["required"])


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
