"""Clipboard helper utilities."""

from __future__ import annotations

import logging

import pyperclip

logger = logging.getLogger("3D Print Uploader")


def copy_to_clipboard(text: str) -> bool:
    """
    Copy text to the system clipboard.

    Returns True on success, False on failure.
    """
    try:
        pyperclip.copy(text)
        logger.debug("Copied to clipboard: %s", text[:80])
        return True
    except pyperclip.PyperclipException as exc:
        logger.error("Clipboard copy failed: %s", exc)
        return False
