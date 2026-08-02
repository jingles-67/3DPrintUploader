"""Tests for the permanent Drive link used by the Beacons button."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from drive import DriveService
from settings import AppSettings
from uploader import Uploader


class _CompletedRequest:
    def next_chunk(self):
        return None, {
            "id": "stable-id",
            "name": "model.stl",
            "webViewLink": "https://drive.google.com/example",
        }


class _FilesResource:
    def __init__(self) -> None:
        self.update_kwargs = None

    def update(self, **kwargs):
        self.update_kwargs = kwargs
        return _CompletedRequest()


class _GoogleService:
    def __init__(self) -> None:
        self.files_resource = _FilesResource()

    def files(self):
        return self.files_resource


class StableDownloadTests(unittest.TestCase):
    def test_drive_update_preserves_configured_file_id(self) -> None:
        service = _GoogleService()
        drive = DriveService(service)

        result = drive.update_file("stable-id", Path(__file__))

        self.assertEqual(result["id"], "stable-id")
        self.assertEqual(
            service.files_resource.update_kwargs["fileId"], "stable-id"
        )

    @patch("uploader.copy_to_clipboard", return_value=False)
    @patch("uploader.open_beacons_in_chrome", return_value=True)
    @patch("uploader.is_internet_available", return_value=True)
    @patch("uploader.DriveService")
    def test_uploader_replaces_permanent_file_instead_of_creating_one(
        self,
        drive_class,
        _internet_check,
        chrome_open,
        _clipboard,
    ) -> None:
        drive = drive_class.return_value
        drive.update_file.return_value = {
            "id": "stable-id",
            "name": "new-model.stl",
            "webViewLink": "https://drive.google.com/example",
        }
        drive.get_download_url.return_value = "https://download.example/stable-id"

        settings = AppSettings(
            beacons_enabled=True,
            beacons_profile_url="https://beacons.ai/example",
            beacons_drive_file_id="stable-id",
            beacons_open_in_chrome=True,
        )
        settings_manager = SimpleNamespace(settings=settings, update=MagicMock())
        auth = SimpleNamespace(ensure_authenticated=MagicMock(return_value=object()))
        history = SimpleNamespace(add=MagicMock())
        uploader = Uploader(auth, settings_manager, history)

        with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as temp_file:
            source = Path(temp_file.name)

        try:
            result = uploader.upload(source)
        finally:
            source.unlink(missing_ok=True)

        drive.update_file.assert_called_once()
        self.assertEqual(drive.update_file.call_args.args[0], "stable-id")
        drive.upload_file.assert_not_called()
        drive.make_public.assert_not_called()
        self.assertEqual(result.drive_id, "stable-id")
        self.assertEqual(result.download_url, "https://download.example/stable-id")
        chrome_open.assert_called_once_with("https://beacons.ai/example")


if __name__ == "__main__":
    unittest.main()
