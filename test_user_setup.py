"""Tests for per-user credentials and installer isolation."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from auth import AuthenticationError, GoogleAuth
from settings import AppSettings


class UserSetupTests(unittest.TestCase):
    def test_user_can_import_own_desktop_credentials(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "downloaded-oauth.json"
            target = root / "app" / "credentials.json"
            token = root / "app" / "token.json"
            source.write_text(
                json.dumps(
                    {
                        "installed": {
                            "client_id": "user.apps.googleusercontent.com",
                            "client_secret": "user-secret",
                            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                            "token_uri": "https://oauth2.googleapis.com/token",
                        }
                    }
                ),
                encoding="utf-8",
            )
            token.parent.mkdir(parents=True)
            token.write_text("old-token", encoding="utf-8")

            auth = GoogleAuth(credentials_path=target, token_path=token)
            auth.import_client_credentials(source)

            self.assertTrue(auth.has_client_credentials)
            self.assertEqual(target.read_text(encoding="utf-8"), source.read_text(encoding="utf-8"))
            self.assertFalse(token.exists())

    def test_non_desktop_credentials_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "wrong.json"
            target = root / "credentials.json"
            source.write_text('{"web": {"client_id": "wrong"}}', encoding="utf-8")
            auth = GoogleAuth(credentials_path=target, token_path=root / "token.json")

            with self.assertRaises(AuthenticationError):
                auth.import_client_credentials(source)

            self.assertFalse(target.exists())

    def test_fresh_install_defaults_have_no_shared_accounts(self) -> None:
        settings = AppSettings()
        self.assertEqual(settings.theme, "system")
        self.assertFalse(settings.beacons_enabled)
        self.assertEqual(settings.beacons_profile_url, "")
        self.assertEqual(settings.beacons_drive_file_id, "")
        self.assertEqual(settings.last_drive_folder_id, "")

    def test_working_copy_contains_no_saved_account_credentials(self) -> None:
        root = Path(__file__).parent
        self.assertFalse((root / "credentials.json").exists())
        self.assertFalse((root / "token.json").exists())
        history_path = root / "history.json"
        if history_path.exists():
            self.assertEqual(
                json.loads(history_path.read_text(encoding="utf-8")),
                [],
            )

    def test_in_app_tutorial_covers_all_setup_services(self) -> None:
        gui_source = (Path(__file__).parent / "gui.py").read_text(encoding="utf-8")
        self.assertIn("class TutorialPage", gui_source)
        self.assertIn("Enable the Google Drive API", gui_source)
        self.assertIn("Import your credentials JSON", gui_source)
        self.assertIn("Connect your Beacons page", gui_source)

    def test_installer_does_not_bundle_personal_configuration(self) -> None:
        script = (Path(__file__).parent / "installer" / "3DPrintUploader.nsi").read_text(
            encoding="utf-8"
        )
        self.assertNotIn('File "${PROJECT_DIR}\\credentials.json"', script)
        self.assertNotIn('File /oname=config.json', script)
        self.assertIn('File "${PROJECT_DIR}\\credentials.json.example"', script)


if __name__ == "__main__":
    unittest.main()
