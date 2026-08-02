"""Tests for automatic release versioning."""

from __future__ import annotations

import unittest

from release import bump_version, parse_version, render_version_info


class ReleaseVersionTests(unittest.TestCase):
    def test_patch_version_increments_for_each_update(self) -> None:
        self.assertEqual(bump_version("1.1.0"), "1.1.1")

    def test_minor_and_major_versions_reset_lower_components(self) -> None:
        self.assertEqual(bump_version("1.9.7", "minor"), "1.10.0")
        self.assertEqual(bump_version("1.9.7", "major"), "2.0.0")

    def test_invalid_version_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            parse_version("version one")

    def test_windows_version_resource_matches_release(self) -> None:
        rendered = render_version_info("2.3.4")
        self.assertIn("filevers=(2, 3, 4, 0)", rendered)
        self.assertIn("ProductVersion', '2.3.4'", rendered)


if __name__ == "__main__":
    unittest.main()
