"""Beacons.ai helpers isolated from the upload workflow."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from urllib.parse import urlparse

logger = logging.getLogger("3D Print Uploader")


def find_chrome_executable() -> Path | None:
    """Return the installed Google Chrome executable, if one is available."""
    candidates: list[Path] = []

    if sys.platform == "win32":
        for variable in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
            root = os.environ.get(variable)
            if root:
                candidates.append(
                    Path(root)
                    / "Google"
                    / "Chrome"
                    / "Application"
                    / "chrome.exe"
                )
    elif sys.platform == "darwin":
        candidates.append(
            Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
        )

    for candidate in candidates:
        if candidate.is_file():
            return candidate

    for command in ("chrome", "google-chrome", "google-chrome-stable"):
        located = shutil.which(command)
        if located:
            return Path(located)
    return None


def open_beacons_in_chrome(url: str) -> bool:
    """Open a safe Beacons web URL in the user's regular Chrome session."""
    parsed = urlparse(url.strip())
    hostname = (parsed.hostname or "").lower()
    is_beacons_host = hostname == "beacons.ai" or hostname.endswith(".beacons.ai")
    if parsed.scheme not in {"http", "https"} or not is_beacons_host:
        logger.warning("Refusing to open invalid Beacons URL: %s", url)
        return False

    chrome = find_chrome_executable()
    if chrome is None:
        logger.warning("Google Chrome was not found.")
        return False

    try:
        subprocess.Popen(
            [str(chrome), url],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
        )
        logger.info("Opened Beacons in Google Chrome: %s", url)
        return True
    except OSError as exc:
        logger.warning("Could not open Beacons in Google Chrome: %s", exc)
        return False


class BeaconsClient(ABC):
    """Abstract interface for a Beacons post-upload action."""

    @abstractmethod
    def update_download_url(self, url: str) -> bool:
        """Attempt an update and return whether it was applied."""

    @abstractmethod
    def is_available(self) -> bool:
        """Return True when this client can be used."""


class NoOpBeaconsClient(BeaconsClient):
    """Client used when Beacons integration is disabled."""

    def update_download_url(self, url: str) -> bool:
        return False

    def is_available(self) -> bool:
        return False


class BrowserBeaconsClient(BeaconsClient):
    """Open Beacons in the user's normal Google Chrome session."""

    def __init__(self, editor_url: str) -> None:
        self._editor_url = editor_url.strip()

    def update_download_url(self, url: str) -> bool:
        if not self.is_available():
            return False
        return open_beacons_in_chrome(self._editor_url)

    def is_available(self) -> bool:
        return bool(self._editor_url)


def create_beacons_client(
    enabled: bool = False,
    profile_url: str = "",
    button_label: str = "download print",
    **_kwargs,
) -> BeaconsClient:
    """Create the optional Chrome-based Beacons client."""
    if enabled and profile_url:
        return BrowserBeaconsClient(profile_url)
    return NoOpBeaconsClient()
