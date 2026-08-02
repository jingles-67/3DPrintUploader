"""Folder-to-ZIP utilities for upload preparation."""

from __future__ import annotations

import logging
import zipfile
from pathlib import Path

from utils import TEMP_DIR

logger = logging.getLogger("3D Print Uploader")


class ZipError(Exception):
    """Raised when ZIP creation fails."""


def create_zip_from_folder(
    folder_path: Path,
    output_path: Path | None = None,
) -> Path:
    """
    Create a ZIP archive from a folder.

    Args:
        folder_path: Directory to compress.
        output_path: Optional output .zip path. Defaults to temp/<folder>.zip.

    Returns:
        Path to the created ZIP file.

    Raises:
        ZipError: If the folder is invalid or compression fails.
    """
    if not folder_path.is_dir():
        raise ZipError(f"Not a directory: {folder_path}")

    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = output_path or (TEMP_DIR / f"{folder_path.name}.zip")

    try:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for file_path in folder_path.rglob("*"):
                if file_path.is_file():
                    arcname = file_path.relative_to(folder_path.parent)
                    zf.write(file_path, arcname)
        logger.info("Created ZIP %s from %s.", zip_path.name, folder_path)
        return zip_path
    except OSError as exc:
        logger.error("ZIP creation failed: %s", exc)
        raise ZipError(f"Could not create ZIP: {exc}") from exc


def cleanup_temp_zip(zip_path: Path) -> None:
    """Remove a temporary ZIP file if it exists."""
    try:
        if zip_path.exists() and zip_path.parent == TEMP_DIR.resolve():
            zip_path.unlink()
            logger.debug("Removed temp ZIP: %s", zip_path.name)
    except OSError as exc:
        logger.warning("Could not remove temp ZIP %s: %s", zip_path, exc)
