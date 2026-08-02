"""Google Drive API operations."""

from __future__ import annotations

import logging
import mimetypes
from pathlib import Path
from typing import Any, Callable, Optional

from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

from utils import direct_download_url

logger = logging.getLogger("3D Print Uploader")


class DriveError(Exception):
    """Raised when a Google Drive operation fails."""


class DrivePermissionError(DriveError):
    """Raised when setting file permissions fails."""


class DriveService:
    """Wrapper around Google Drive API v3."""

    def __init__(self, service: Any) -> None:
        self._service = service

    def list_folders(
        self,
        parent_id: str = "root",
        page_size: int = 100,
    ) -> list[dict[str, str]]:
        """
        List subfolders within a parent folder.

        Returns:
            List of dicts with keys: id, name.
        """
        query = (
            f"'{parent_id}' in parents and "
            "mimeType='application/vnd.google-apps.folder' and trashed=false"
        )
        try:
            response = (
                self._service.files()
                .list(
                    q=query,
                    spaces="drive",
                    fields="files(id, name)",
                    pageSize=page_size,
                    orderBy="name",
                )
                .execute()
            )
            folders = response.get("files", [])
            logger.debug("Listed %d folders under %s.", len(folders), parent_id)
            return folders
        except HttpError as exc:
            logger.error("Failed to list folders: %s", exc)
            raise DriveError(f"Could not list Drive folders: {exc}") from exc

    def get_folder_name(self, folder_id: str) -> str:
        """Return the display name of a folder, or a fallback label."""
        if not folder_id or folder_id == "root":
            return "My Drive"
        try:
            meta = (
                self._service.files()
                .get(fileId=folder_id, fields="name")
                .execute()
            )
            return meta.get("name", "Unknown Folder")
        except HttpError as exc:
            logger.warning("Could not fetch folder name for %s: %s", folder_id, exc)
            return "Unknown Folder"

    def upload_file(
        self,
        file_path: Path,
        folder_id: str = "",
        progress_callback: Optional[Callable[[int], None]] = None,
        chunk_size: int = 256 * 1024,
    ) -> dict[str, str]:
        """
        Upload a file using resumable upload.

        Args:
            file_path: Local file to upload.
            folder_id: Destination Drive folder ID (empty = root).
            progress_callback: Called with percent complete (0-100).
            chunk_size: Upload chunk size in bytes.

        Returns:
            Dict with keys: id, name, webViewLink.
        """
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if not mime_type:
            mime_type = "application/octet-stream"

        metadata: dict[str, Any] = {"name": file_path.name}
        if folder_id:
            metadata["parents"] = [folder_id]

        media = MediaFileUpload(
            str(file_path),
            mimetype=mime_type,
            resumable=True,
            chunksize=chunk_size,
        )

        request = self._service.files().create(
            body=metadata,
            media_body=media,
            fields="id, name, webViewLink",
        )

        response = None
        try:
            while response is None:
                status, response = request.next_chunk()
                if status and progress_callback:
                    progress_callback(int(status.progress() * 100))
        except HttpError as exc:
            logger.error("Upload failed for %s: %s", file_path.name, exc)
            raise DriveError(f"Upload failed: {exc}") from exc

        if progress_callback:
            progress_callback(100)

        logger.info("Uploaded %s -> %s", file_path.name, response["id"])
        return {
            "id": response["id"],
            "name": response["name"],
            "webViewLink": response.get("webViewLink", ""),
        }

    def make_public(self, file_id: str) -> None:
        """
        Set file permission to anyone with the link (reader).

        Raises:
            PermissionError: If the permission cannot be set.
        """
        permission = {"type": "anyone", "role": "reader"}
        try:
            self._service.permissions().create(
                fileId=file_id,
                body=permission,
            ).execute()
            logger.info("Set public read permission on %s.", file_id)
        except HttpError as exc:
            logger.error("Permission failed for %s: %s", file_id, exc)
            raise DrivePermissionError(
                f"Could not make file public: {exc}"
            ) from exc

    def update_file(
        self,
        file_id: str,
        file_path: Path,
        progress_callback: Optional[Callable[[int], None]] = None,
        chunk_size: int = 256 * 1024,
    ) -> dict[str, str]:
        """Replace a Drive file's content while preserving its public ID."""
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if not mime_type:
            mime_type = "application/octet-stream"

        media = MediaFileUpload(
            str(file_path),
            mimetype=mime_type,
            resumable=True,
            chunksize=chunk_size,
        )
        request = self._service.files().update(
            fileId=file_id,
            body={"name": file_path.name, "mimeType": mime_type},
            media_body=media,
            fields="id, name, webViewLink",
        )

        response = None
        try:
            while response is None:
                status, response = request.next_chunk()
                if status and progress_callback:
                    progress_callback(int(status.progress() * 100))
        except HttpError as exc:
            logger.error("Update failed for Drive file %s: %s", file_id, exc)
            raise DriveError(f"Could not update permanent download file: {exc}") from exc

        if progress_callback:
            progress_callback(100)

        logger.info("Updated %s with %s", file_id, file_path.name)
        return {
            "id": response["id"],
            "name": response["name"],
            "webViewLink": response.get("webViewLink", ""),
        }

    def get_download_url(self, file_id: str) -> str:
        """Return the direct download URL for a file."""
        return direct_download_url(file_id)

    def delete_file(self, file_id: str) -> None:
        """Permanently delete a file from Drive."""
        try:
            self._service.files().delete(fileId=file_id).execute()
            logger.info("Deleted Drive file %s.", file_id)
        except HttpError as exc:
            logger.error("Delete failed for %s: %s", file_id, exc)
            raise DriveError(f"Could not delete file: {exc}") from exc
