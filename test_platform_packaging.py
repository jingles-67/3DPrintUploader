"""Tests for Linux, macOS, and portable release packaging."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile


class PlatformPackagingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(__file__).parent

    def test_every_requested_release_target_has_a_builder(self) -> None:
        self.assertTrue((self.root / "packaging" / "linux.spec").is_file())
        self.assertTrue((self.root / "packaging" / "macos.spec").is_file())
        self.assertTrue((self.root / "packaging" / "build_linux.sh").is_file())
        self.assertTrue((self.root / "packaging" / "build_macos.sh").is_file())
        self.assertTrue((self.root / "packaging" / "build_portable.py").is_file())

    def test_github_workflow_builds_all_platforms(self) -> None:
        workflow = (
            self.root / ".github" / "workflows" / "build-multiplatform.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("runs-on: windows-latest", workflow)
        self.assertIn("runner: ubuntu-22.04", workflow)
        self.assertIn("runner: ubuntu-24.04-arm", workflow)
        self.assertIn("runner: macos-15", workflow)
        self.assertIn("runner: macos-15-intel", workflow)
        self.assertIn("release-other-files", workflow)
        self.assertIn("gh release upload", workflow)

    def test_packaged_unix_data_locations_are_per_user(self) -> None:
        source = (self.root / "utils.py").read_text(encoding="utf-8")
        self.assertIn('"Library" / "Application Support" / APP_NAME', source)
        self.assertIn('os.environ.get("XDG_CONFIG_HOME"', source)
        self.assertIn('APP_DIR = config_home / "3d-print-uploader"', source)

    def test_other_files_archive_excludes_private_data(self) -> None:
        script_path = self.root / "packaging" / "build_portable.py"
        spec = importlib.util.spec_from_file_location("portable_builder", script_path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        with tempfile.TemporaryDirectory() as temp_dir:
            archive_path = module.build_archive(Path(temp_dir))
            with ZipFile(archive_path) as archive:
                names = {Path(name).name for name in archive.namelist()}
                paths = set(archive.namelist())

        for private_name in (
            "credentials.json",
            "token.json",
            "config.json",
            "history.json",
            "app.log",
        ):
            self.assertNotIn(private_name, names)
        self.assertIn("credentials.json.example", names)
        self.assertIn("run.sh", names)
        self.assertFalse(any("dist-" in path or "build-" in path for path in paths))


if __name__ == "__main__":
    unittest.main()
