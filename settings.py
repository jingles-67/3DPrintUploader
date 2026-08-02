"""Application settings persistence."""

from __future__ import annotations

import json
import logging
from copy import deepcopy
from dataclasses import asdict, dataclass
from typing import Any

from utils import CONFIG_PATH

logger = logging.getLogger("3D Print Uploader")


@dataclass
class AppSettings:
    """User-configurable application settings."""

    theme: str = "system"
    last_drive_folder_id: str = ""
    last_drive_folder_name: str = "My Drive"
    window_width: int = 960
    window_height: int = 720
    auto_copy_link: bool = True
    auto_open_link: bool = False
    default_upload_folder: str = ""
    beacons_enabled: bool = False
    beacons_profile_url: str = ""
    beacons_button_label: str = "download print"
    beacons_drive_file_id: str = ""
    beacons_open_in_chrome: bool = True

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AppSettings:
        """Create settings from a dictionary, ignoring unknown keys."""
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)

    def to_dict(self) -> dict[str, Any]:
        """Serialize settings to a plain dictionary."""
        return asdict(self)


class SettingsManager:
    """Load, save, and expose application settings."""

    DEFAULTS = AppSettings()

    def __init__(self, config_path=CONFIG_PATH) -> None:
        self._path = config_path
        self._settings = self.load()

    @property
    def settings(self) -> AppSettings:
        return self._settings

    def load(self) -> AppSettings:
        """Load settings from disk or return defaults."""
        if not self._path.exists():
            logger.info("No config found; using defaults.")
            return deepcopy(self.DEFAULTS)

        try:
            with self._path.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
            settings = AppSettings.from_dict(data)
            logger.debug("Settings loaded from %s", self._path)
            return settings
        except (OSError, json.JSONDecodeError, TypeError) as exc:
            logger.error("Failed to load settings: %s", exc)
            return deepcopy(self.DEFAULTS)

    def save(self) -> None:
        """Persist current settings to disk."""
        try:
            with self._path.open("w", encoding="utf-8") as fh:
                json.dump(self._settings.to_dict(), fh, indent=2)
            logger.debug("Settings saved to %s", self._path)
        except OSError as exc:
            logger.error("Failed to save settings: %s", exc)
            raise

    def update(self, **kwargs: Any) -> None:
        """Update one or more settings fields and save."""
        for key, value in kwargs.items():
            if hasattr(self._settings, key):
                setattr(self._settings, key, value)
            else:
                logger.warning("Ignoring unknown setting: %s", key)
        self.save()

    def reset(self) -> None:
        """Reset all settings to defaults."""
        self._settings = deepcopy(self.DEFAULTS)
        self.save()
