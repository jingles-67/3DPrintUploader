"""Shared utilities for the 3D Print Uploader application."""

from __future__ import annotations

import logging
import os
import socket
import sys
from pathlib import Path
from typing import Final

# Supported 3D print file extensions (lowercase, with leading dot).
SUPPORTED_EXTENSIONS: Final[frozenset[str]] = frozenset(
    {".stl", ".3mf", ".step", ".stp", ".obj", ".zip"}
)

APP_NAME: Final[str] = "3D Print Uploader"

# Resolve application root — works for both script and PyInstaller bundle.
if getattr(sys, "frozen", False):
    executable_dir = Path(sys.executable).parent
    if sys.platform == "win32":
        project_dir = executable_dir.parent
        # Keep compatibility with existing Windows development builds and
        # per-user NSIS installs.
        if not (executable_dir / "credentials.json").exists() and (
            project_dir / "credentials.json"
        ).exists():
            APP_DIR: Final[Path] = project_dir
        else:
            APP_DIR = executable_dir
    elif sys.platform == "darwin":
        # An application bundle is not a safe writable data location.
        APP_DIR = Path.home() / "Library" / "Application Support" / APP_NAME
    else:
        # Ubuntu, Linux Mint, and other freedesktop-compatible distributions.
        config_home = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
        APP_DIR = config_home / "3d-print-uploader"
else:
    APP_DIR = Path(__file__).resolve().parent

# Static resources are extracted beneath ``sys._MEIPASS`` by a PyInstaller
# one-file build. In source runs they live directly in the project folder.
RESOURCE_DIR: Final[Path] = Path(getattr(sys, "_MEIPASS", APP_DIR))


def _read_app_version() -> str:
    """Read the release version bundled with source and packaged builds."""
    try:
        return (RESOURCE_DIR / "VERSION").read_text(encoding="utf-8").strip()
    except OSError:
        return "0.0.0"


APP_VERSION: Final[str] = _read_app_version()

CONFIG_PATH: Final[Path] = APP_DIR / "config.json"
HISTORY_PATH: Final[Path] = APP_DIR / "history.json"
LOG_PATH: Final[Path] = APP_DIR / "app.log"
TEMP_DIR: Final[Path] = APP_DIR / "temp"
ASSETS_DIR: Final[Path] = APP_DIR / "assets"
ICONS_DIR: Final[Path] = ASSETS_DIR / "icons"
APP_ICON_PATH: Final[Path] = RESOURCE_DIR / "assets" / "icons" / "app_icon.ico"
APP_ICON_PNG_PATH: Final[Path] = (
    RESOURCE_DIR / "assets" / "icons" / "app_icon.png"
)
RED_GREEN_THEME_PATH: Final[Path] = (
    RESOURCE_DIR / "assets" / "themes" / "red_green.json"
)
CREDENTIALS_PATH: Final[Path] = APP_DIR / "credentials.json"
TOKEN_PATH: Final[Path] = APP_DIR / "token.json"


def ensure_directories() -> None:
    """Create runtime directories if they do not exist."""
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    ICONS_DIR.mkdir(parents=True, exist_ok=True)


def setup_logging() -> logging.Logger:
    """Configure application-wide logging to file and console."""
    ensure_directories()
    logger = logging.getLogger(APP_NAME)
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = logging.FileHandler(LOG_PATH, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger


def direct_download_url(file_id: str) -> str:
    """Build a direct Google Drive download URL from a file ID."""
    return f"https://drive.google.com/uc?export=download&id={file_id}"


def is_supported_file(path: Path) -> bool:
    """Return True if the path has a supported 3D print extension."""
    return path.suffix.lower() in SUPPORTED_EXTENSIONS


def is_internet_available(timeout: float = 3.0) -> bool:
    """Check internet connectivity without changing global socket settings."""
    try:
        # Do not use socket.setdefaulttimeout() here.  Its process-wide value is
        # inherited by the local HTTP server used during Google OAuth, causing
        # that server to stop waiting for the browser callback after 3 seconds.
        with socket.create_connection(("drive.google.com", 443), timeout=timeout):
            pass
        return True
    except OSError:
        return False


def human_size(num_bytes: int) -> str:
    """Format a byte count as a human-readable string."""
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} PB"


def parse_dropped_paths(raw: str) -> list[Path]:
    """Parse tkinterdnd2 DND_FILES payload into Path objects."""
    paths: list[Path] = []
    token = ""
    in_braces = False

    for char in raw:
        if char == "{":
            in_braces = True
            token = ""
        elif char == "}":
            in_braces = False
            if token:
                paths.append(Path(token))
            token = ""
        elif char == " " and not in_braces:
            if token:
                paths.append(Path(token))
                token = ""
        else:
            token += char

    if token:
        paths.append(Path(token))
    return paths
