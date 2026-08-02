"""Tests for the bundled red-and-green application theme."""

from __future__ import annotations

import json
import unittest

import customtkinter as ctk

from settings import AppSettings
from utils import RED_GREEN_THEME_PATH


class RedGreenThemeTests(unittest.TestCase):
    def test_theme_file_contains_main_widget_palettes(self) -> None:
        with RED_GREEN_THEME_PATH.open("r", encoding="utf-8") as theme_file:
            theme = json.load(theme_file)

        for widget in (
            "CTk",
            "CTkFrame",
            "CTkButton",
            "CTkEntry",
            "CTkSwitch",
            "CTkProgressBar",
            "CTkOptionMenu",
        ):
            self.assertIn(widget, theme)

        self.assertEqual(theme["CTkButton"]["fg_color"][1], "#B83232")
        self.assertEqual(theme["CTkSwitch"]["progress_color"][1], "#39A96B")

    def test_system_is_the_default_theme(self) -> None:
        self.assertEqual(AppSettings().theme, "system")

    def test_customtkinter_accepts_the_theme_file(self) -> None:
        ctk.set_default_color_theme(str(RED_GREEN_THEME_PATH))
        self.assertEqual(
            ctk.ThemeManager.theme["CTkButton"]["fg_color"][1],
            "#B83232",
        )
        ctk.set_default_color_theme("blue")


if __name__ == "__main__":
    unittest.main()
