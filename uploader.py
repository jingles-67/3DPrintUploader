"""Upload orchestration with retries and progress reporting."""

from __future__ import annotations

import logging
import time
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from auth import AuthenticationError, GoogleAuth
from beacons import open_beacons_in_chrome
from clipboard import copy_to_clipboard
from drive import DriveError, DrivePermissionError, DriveService
from history import HistoryManager, HistoryRecord
from settings import SettingsManager
from utils import is_internet_available, is_supported_file
from zipper import ZipError, cleanup_temp_zip, create_zip_from_folder

logger = logging.getLogger("3D Print Uploader")


@dataclass
class UploadResult:
    """Result of a successful upload."""

    filename: str
    drive_id: str
    download_url: str
    web_view_link: str


class UploadError(Exception):
    """Raised when an upload cannot be completed."""


ProgressCallback = Callable[[str], None]
PercentCallback = Callable[[int], None]


class Uploader:
    """
    Coordinate file preparation, Drive upload, sharing, and post-upload actions.
    """

    MAX_RETRIES = 3
    RETRY_DELAY_SECONDS = 2.0

    def __init__(
        self,
        auth: GoogleAuth,
        settings: SettingsManager,
        history: HistoryManager,
    ) -> None:
        self._auth = auth
        self._settings = settings
        self._history = history

    def prepare_upload_path(self, source: Path) -> tuple[Path, bool]:
        """
        Resolve the file to upload.

        Returns:
            Tuple of (upload_path, is_temp_zip).
        """
        source = source.resolve()

        if source.is_dir():
            zip_path = create_zip_from_folder(source)
            return zip_path, True

        if not source.is_file():
            raise UploadError(f"Path not found: {source}")

        if not is_supported_file(source):
            raise UploadError(
                f"Unsupported file type: {source.suffix}. "
                f"Supported: .stl, .3mf, .step, .obj, .zip"
            )

        return source, False

    def upload(
        self,
        source: Path,
        on_status: Optional[ProgressCallback] = None,
        on_progress: Optional[PercentCallback] = None,
    ) -> UploadResult:
        """
        Upload a file or folder to Google Drive with retries.

        Args:
            source: File or folder path.
            on_status: Status message callback.
            on_progress: Upload percent callback (0-100).

        Returns:
            UploadResult on success.

        Raises:
            UploadError: On validation or unrecoverable failure.
        """
        if not is_internet_available():
            raise UploadError(
                "No internet connection. Check your network and try again."
            )

        upload_path, is_temp = self.prepare_upload_path(source)
        settings = self._settings.settings
        folder_id = settings.last_drive_folder_id
        permanent_file_id = (
            settings.beacons_drive_file_id if settings.beacons_enabled else ""
        )

        def status(msg: str) -> None:
            logger.info(msg)
            if on_status:
                on_status(msg)

        last_error: Optional[Exception] = None

        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                status(
                    f"Authenticating..."
                    if attempt == 1
                    else f"Retrying upload (attempt {attempt}/{self.MAX_RETRIES})..."
                )
                service = self._auth.ensure_authenticated(on_progress=status)
                drive = DriveService(service)

                if permanent_file_id:
                    status(
                        f"Updating permanent download with {upload_path.name}..."
                    )
                    file_meta = drive.update_file(
                        permanent_file_id,
                        upload_path,
                        progress_callback=on_progress,
                    )
                    status("Beacons download updated automatically.")
                else:
                    status(f"Uploading {upload_path.name}...")
                    file_meta = drive.upload_file(
                        upload_path,
                        folder_id=folder_id,
                        progress_callback=on_progress,
                    )

                    status("Setting public sharing permissions...")
                    drive.make_public(file_meta["id"])
                    if settings.beacons_enabled:
                        permanent_file_id = file_meta["id"]
                        self._settings.update(
                            beacons_drive_file_id=permanent_file_id
                        )

                download_url = drive.get_download_url(file_meta["id"])

                result = UploadResult(
                    filename=file_meta["name"],
                    drive_id=file_meta["id"],
                    download_url=download_url,
                    web_view_link=file_meta.get("webViewLink", ""),
                )

                self._post_upload_actions(result, status)
                return result

            except (AuthenticationError, DriveError, DrivePermissionError) as exc:
                last_error = exc
                logger.warning(
                    "Upload attempt %d failed: %s", attempt, exc
                )
                if attempt < self.MAX_RETRIES:
                    time.sleep(self.RETRY_DELAY_SECONDS * attempt)
                else:
                    break
            finally:
                if is_temp:
                    cleanup_temp_zip(upload_path)

        raise UploadError(
            f"Upload failed after {self.MAX_RETRIES} attempts: {last_error}"
        )

    def _post_upload_actions(
        self,
        result: UploadResult,
        status: ProgressCallback,
    ) -> None:
        """Handle history, clipboard, and browser actions after upload."""
        record = HistoryRecord.create(
            filename=result.filename,
            drive_id=result.drive_id,
            download_url=result.download_url,
        )
        self._history.add(record)
        status("Upload complete.")

        settings = self._settings.settings

        if settings.auto_copy_link:
            if copy_to_clipboard(result.download_url):
                status("Download link copied to clipboard.")

        if settings.auto_open_link:
            webbrowser.open(result.download_url)
            status("Opened download link in browser.")

        if settings.beacons_enabled:
            status("Beacons is live on the permanent download link.")
            if settings.beacons_open_in_chrome and settings.beacons_profile_url:
                if open_beacons_in_chrome(settings.beacons_profile_url):
                    status("Opened Beacons in Google Chrome.")
                else:
                    status("Beacons updated, but Google Chrome could not be opened.")

