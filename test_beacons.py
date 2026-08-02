"""Tests for the Chrome-based Beacons helper."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from beacons import open_beacons_in_chrome


class BeaconsChromeTests(unittest.TestCase):
    @patch("beacons.subprocess.Popen")
    @patch(
        "beacons.find_chrome_executable",
        return_value=Path(r"C:\Program Files\Google\Chrome\chrome.exe"),
    )
    def test_opens_beacons_url_in_chrome(self, _find_chrome, popen) -> None:
        opened = open_beacons_in_chrome("https://beacons.ai/example")

        self.assertTrue(opened)
        popen.assert_called_once_with(
            [
                r"C:\Program Files\Google\Chrome\chrome.exe",
                "https://beacons.ai/example",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
        )

    @patch("beacons.find_chrome_executable")
    def test_rejects_non_beacons_url(self, find_chrome) -> None:
        opened = open_beacons_in_chrome("https://example.com/not-beacons")

        self.assertFalse(opened)
        find_chrome.assert_not_called()


if __name__ == "__main__":
    unittest.main()
