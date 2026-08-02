"""Upload history persistence and management."""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

from utils import HISTORY_PATH

logger = logging.getLogger("3D Print Uploader")


@dataclass
class HistoryRecord:
    """A single upload history entry."""

    id: str
    filename: str
    upload_date: str
    drive_id: str
    download_url: str

    @classmethod
    def create(
        cls,
        filename: str,
        drive_id: str,
        download_url: str,
    ) -> HistoryRecord:
        """Create a new history record with generated ID and timestamp."""
        return cls(
            id=str(uuid.uuid4()),
            filename=filename,
            upload_date=datetime.now(timezone.utc).isoformat(),
            drive_id=drive_id,
            download_url=download_url,
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HistoryRecord:
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            filename=data["filename"],
            upload_date=data["upload_date"],
            drive_id=data["drive_id"],
            download_url=data["download_url"],
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class HistoryManager:
    """Manage upload history stored in history.json."""

    def __init__(self, history_path=HISTORY_PATH) -> None:
        self._path = history_path
        self._records: list[HistoryRecord] = self._load()

    @property
    def records(self) -> list[HistoryRecord]:
        """Return records newest-first."""
        return list(self._records)

    def _load(self) -> list[HistoryRecord]:
        if not self._path.exists():
            return []

        try:
            with self._path.open("r", encoding="utf-8") as fh:
                raw = json.load(fh)
            records = [HistoryRecord.from_dict(item) for item in raw]
            records.sort(key=lambda r: r.upload_date, reverse=True)
            logger.debug("Loaded %d history records.", len(records))
            return records
        except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
            logger.error("Failed to load history: %s", exc)
            return []

    def _save(self) -> None:
        try:
            with self._path.open("w", encoding="utf-8") as fh:
                json.dump([r.to_dict() for r in self._records], fh, indent=2)
        except OSError as exc:
            logger.error("Failed to save history: %s", exc)
            raise

    def add(self, record: HistoryRecord) -> None:
        """Append a record and persist."""
        self._records.insert(0, record)
        self._save()
        logger.info("History added: %s", record.filename)

    def delete(self, record_id: str) -> bool:
        """Delete a record by ID. Returns True if found."""
        before = len(self._records)
        self._records = [r for r in self._records if r.id != record_id]
        if len(self._records) < before:
            self._save()
            logger.info("History deleted: %s", record_id)
            return True
        return False

    def clear(self) -> None:
        """Remove all history records."""
        self._records.clear()
        self._save()
        logger.info("History cleared.")
