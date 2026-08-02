"""CustomTkinter GUI for the 3D Print Uploader."""

from __future__ import annotations

import logging
import sys
import threading
import webbrowser
from datetime import datetime
from pathlib import Path
from tkinter import Menu, PhotoImage, filedialog, messagebox
from typing import Callable, Optional

import customtkinter as ctk
from tkinterdnd2 import DND_FILES, TkinterDnD

from auth import AuthenticationError, GoogleAuth
from clipboard import copy_to_clipboard
from drive import DriveError, DriveService
from history import HistoryManager, HistoryRecord
from qrcode_util import qr_to_photoimage
from settings import AppSettings, SettingsManager
from uploader import UploadError, UploadResult, Uploader
from utils import (
    APP_ICON_PATH,
    APP_ICON_PNG_PATH,
    APP_NAME,
    APP_VERSION,
    CREDENTIALS_PATH,
    RED_GREEN_THEME_PATH,
    SUPPORTED_EXTENSIONS,
    human_size,
    parse_dropped_paths,
)

logger = logging.getLogger("3D Print Uploader")

# Appearance constants
CORNER_RADIUS = 12
BTN_HEIGHT = 36
PAD = 16
ACCENT_RED = "#C83232"
ACCENT_RED_HOVER = "#A72626"
ACCENT_GREEN = "#2E8B57"
ACCENT_GREEN_HOVER = "#247347"


class StatusBar(ctk.CTkFrame):
    """Bottom status bar showing messages and progress."""

    def __init__(self, master, **kwargs) -> None:
        super().__init__(master, height=48, corner_radius=0, **kwargs)
        self.grid_columnconfigure(0, weight=1)

        self._label = ctk.CTkLabel(self, text="Ready", anchor="w")
        self._label.grid(row=0, column=0, padx=PAD, pady=8, sticky="ew")

        self._progress = ctk.CTkProgressBar(self, width=180)
        self._progress.grid(row=0, column=1, padx=PAD, pady=8)
        self._progress.set(0)
        self._progress.grid_remove()

    def set_message(self, text: str) -> None:
        self._label.configure(text=text)

    def show_progress(self, show: bool = True) -> None:
        if show:
            self._progress.grid()
        else:
            self._progress.grid_remove()
            self._progress.set(0)

    def set_progress(self, value: float) -> None:
        self._progress.set(max(0.0, min(1.0, value / 100.0)))


class UploadPage(ctk.CTkFrame):
    """Main upload page with drag-and-drop."""

    def __init__(
        self,
        master,
        on_upload: Callable[[Path], None],
        on_browse: Callable[[], None],
        on_browse_folder: Callable[[], None] | None = None,
        **kwargs,
    ) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self._on_upload = on_upload
        self._on_browse = on_browse
        self._on_browse_folder = on_browse_folder or on_browse
        self._selected: Optional[Path] = None
        self._qr_photo = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        title = ctk.CTkLabel(
            self,
            text="Upload 3D Print Files",
            font=ctk.CTkFont(size=22, weight="bold"),
        )
        title.grid(row=0, column=0, padx=PAD, pady=(PAD, 8), sticky="w")

        self._drop_frame = ctk.CTkFrame(
            self, corner_radius=CORNER_RADIUS, border_width=2
        )
        self._drop_frame.grid(row=1, column=0, padx=PAD, pady=8, sticky="nsew")
        self._drop_frame.grid_columnconfigure(0, weight=1)
        self._drop_frame.grid_rowconfigure(0, weight=1)

        exts = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        self._drop_label = ctk.CTkLabel(
            self._drop_frame,
            text=f"Drag & drop files or folders here\n\nSupported: {exts}",
            font=ctk.CTkFont(size=14),
            justify="center",
        )
        self._drop_label.grid(row=0, column=0, padx=32, pady=48)

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.grid(row=2, column=0, padx=PAD, pady=8, sticky="ew")

        self._browse_btn = ctk.CTkButton(
            btn_row,
            text="Browse Files",
            corner_radius=CORNER_RADIUS,
            height=BTN_HEIGHT,
            command=self._on_browse,
        )
        self._browse_btn.pack(side="left", padx=(0, 8))

        self._browse_folder_btn = ctk.CTkButton(
            btn_row,
            text="Browse Folder",
            corner_radius=CORNER_RADIUS,
            height=BTN_HEIGHT,
            command=self._on_browse_folder,
        )
        self._browse_folder_btn.pack(side="left", padx=(0, 8))

        self._upload_btn = ctk.CTkButton(
            btn_row,
            text="Upload to Google Drive",
            corner_radius=CORNER_RADIUS,
            height=BTN_HEIGHT,
            fg_color=ACCENT_GREEN,
            hover_color=ACCENT_GREEN_HOVER,
            state="disabled",
            command=self._trigger_upload,
        )
        self._upload_btn.pack(side="left")

        result_frame = ctk.CTkFrame(self, corner_radius=CORNER_RADIUS)
        result_frame.grid(row=3, column=0, padx=PAD, pady=PAD, sticky="ew")
        result_frame.grid_columnconfigure(0, weight=1)

        self._url_entry = ctk.CTkEntry(
            result_frame, placeholder_text="Download link will appear here"
        )
        self._url_entry.grid(row=0, column=0, padx=12, pady=12, sticky="ew")

        self._copy_btn = ctk.CTkButton(
            result_frame,
            text="Copy Link",
            width=100,
            corner_radius=CORNER_RADIUS,
            height=BTN_HEIGHT,
            command=self._copy_link,
        )
        self._copy_btn.grid(row=0, column=1, padx=(0, 12), pady=12)

        self._open_btn = ctk.CTkButton(
            result_frame,
            text="Open",
            width=80,
            corner_radius=CORNER_RADIUS,
            height=BTN_HEIGHT,
            command=self._open_link,
        )
        self._open_btn.grid(row=0, column=2, padx=(0, 12), pady=12)

        self._qr_label = ctk.CTkLabel(result_frame, text="")
        self._qr_label.grid(row=1, column=0, columnspan=3, pady=(0, 12))

    def enable_dnd(self) -> None:
        """Register drag-and-drop on the drop zone."""
        self._drop_frame.drop_target_register(DND_FILES)
        self._drop_frame.dnd_bind("<<Drop>>", self._on_drop)

    def _on_drop(self, event) -> None:
        paths = parse_dropped_paths(event.data)
        if paths:
            self.set_selected(paths[0])

    def _trigger_upload(self) -> None:
        if self._selected:
            self._on_upload(self._selected)

    def set_selected(self, path: Path) -> None:
        self._selected = path
        if path.is_dir():
            label = f"Folder: {path.name}"
        else:
            try:
                size = human_size(path.stat().st_size)
                label = f"File: {path.name} ({size})"
            except OSError:
                label = f"File: {path.name}"
        self._drop_label.configure(text=label)
        self._upload_btn.configure(state="normal")

    def clear_selection(self) -> None:
        exts = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        self._drop_label.configure(
            text=f"Drag & drop files or folders here\n\nSupported: {exts}"
        )
        self._selected = None
        self._upload_btn.configure(state="disabled")

    def show_result(self, result: UploadResult) -> None:
        self._url_entry.delete(0, "end")
        self._url_entry.insert(0, result.download_url)
        self._qr_photo = qr_to_photoimage(result.download_url, size=160)
        if self._qr_photo:
            self._qr_label.configure(image=self._qr_photo, text="")

    def _copy_link(self) -> None:
        url = self._url_entry.get().strip()
        if url and copy_to_clipboard(url):
            messagebox.showinfo(APP_NAME, "Link copied to clipboard.")

    def _open_link(self) -> None:
        url = self._url_entry.get().strip()
        if url:
            webbrowser.open(url)


class HistoryPage(ctk.CTkFrame):
    """Upload history list with delete support."""

    def __init__(
        self,
        master,
        history: HistoryManager,
        on_refresh: Callable[[], None],
        **kwargs,
    ) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self._history = history
        self._on_refresh = on_refresh

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, padx=PAD, pady=PAD, sticky="ew")
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text="Upload History",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            header,
            text="Clear All",
            width=100,
            corner_radius=CORNER_RADIUS,
            height=BTN_HEIGHT,
            fg_color=ACCENT_RED,
            hover_color=ACCENT_RED_HOVER,
            command=self._clear_all,
        ).grid(row=0, column=1, padx=4)

        ctk.CTkButton(
            header,
            text="Refresh",
            width=100,
            corner_radius=CORNER_RADIUS,
            height=BTN_HEIGHT,
            command=self.refresh,
        ).grid(row=0, column=2)

        self._scroll = ctk.CTkScrollableFrame(self, corner_radius=CORNER_RADIUS)
        self._scroll.grid(row=1, column=0, padx=PAD, pady=(0, PAD), sticky="nsew")
        self._scroll.grid_columnconfigure(0, weight=1)

    def refresh(self) -> None:
        for widget in self._scroll.winfo_children():
            widget.destroy()

        records = self._history.records
        if not records:
            ctk.CTkLabel(
                self._scroll, text="No uploads yet.", text_color="gray"
            ).grid(row=0, column=0, pady=24)
            return

        for idx, record in enumerate(records):
            self._add_row(idx, record)

    def _add_row(self, row: int, record: HistoryRecord) -> None:
        frame = ctk.CTkFrame(self._scroll, corner_radius=8)
        frame.grid(row=row, column=0, padx=4, pady=4, sticky="ew")
        frame.grid_columnconfigure(1, weight=1)

        try:
            dt = datetime.fromisoformat(record.upload_date.replace("Z", "+00:00"))
            date_str = dt.strftime("%Y-%m-%d %H:%M")
        except ValueError:
            date_str = record.upload_date

        ctk.CTkLabel(
            frame,
            text=record.filename,
            font=ctk.CTkFont(weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, columnspan=3, padx=12, pady=(8, 0), sticky="w")

        ctk.CTkLabel(
            frame, text=date_str, text_color="gray", anchor="w", font=ctk.CTkFont(size=12)
        ).grid(row=1, column=0, columnspan=3, padx=12, pady=(0, 4), sticky="w")

        ctk.CTkButton(
            frame,
            text="Copy",
            width=70,
            height=28,
            corner_radius=8,
            command=lambda u=record.download_url: self._copy(u),
        ).grid(row=2, column=0, padx=12, pady=8)

        ctk.CTkButton(
            frame,
            text="Open",
            width=70,
            height=28,
            corner_radius=8,
            command=lambda u=record.download_url: webbrowser.open(u),
        ).grid(row=2, column=1, padx=4, pady=8, sticky="w")

        ctk.CTkButton(
            frame,
            text="Delete",
            width=70,
            height=28,
            corner_radius=8,
            fg_color=ACCENT_RED,
            hover_color=ACCENT_RED_HOVER,
            command=lambda rid=record.id: self._delete(rid),
        ).grid(row=2, column=2, padx=12, pady=8, sticky="e")

    def _copy(self, url: str) -> None:
        if copy_to_clipboard(url):
            messagebox.showinfo(APP_NAME, "Link copied to clipboard.")

    def _delete(self, record_id: str) -> None:
        if messagebox.askyesno(APP_NAME, "Delete this history entry?"):
            self._history.delete(record_id)
            self.refresh()
            self._on_refresh()

    def _clear_all(self) -> None:
        if messagebox.askyesno(
            APP_NAME, "Clear all upload history? This cannot be undone."
        ):
            self._history.clear()
            self.refresh()
            self._on_refresh()


class SettingsPage(ctk.CTkFrame):
    """Application settings editor."""

    def __init__(
        self,
        master,
        settings_mgr: SettingsManager,
        on_theme_change: Callable[[str], None],
        on_save: Callable[[], None],
        on_import_credentials: Callable[[], None],
        on_choose_drive_folder: Callable[[], None],
        **kwargs,
    ) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self._settings_mgr = settings_mgr
        self._on_theme_change = on_theme_change
        self._on_save = on_save
        self._on_import_credentials = on_import_credentials
        self._on_choose_drive_folder = on_choose_drive_folder

        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self,
            text="Settings",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).grid(row=0, column=0, padx=PAD, pady=PAD, sticky="w")

        form = ctk.CTkScrollableFrame(self, corner_radius=CORNER_RADIUS)
        form.grid(row=1, column=0, padx=PAD, pady=(0, PAD), sticky="nsew")
        form.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        s = settings_mgr.settings
        row = 0

        row = self._add_label(form, row, "Theme")
        self._theme_var = ctk.StringVar(value=s.theme)
        theme_menu = ctk.CTkOptionMenu(
            form,
            values=["red-green", "dark", "light", "system"],
            variable=self._theme_var,
            corner_radius=CORNER_RADIUS,
            command=self._theme_changed,
        )
        theme_menu.grid(row=row, column=1, padx=12, pady=8, sticky="ew")
        row += 1

        row = self._add_label(form, row, "Google credentials")
        credentials_row = ctk.CTkFrame(form, fg_color="transparent")
        credentials_row.grid(row=row, column=1, padx=12, pady=8, sticky="ew")
        credentials_row.grid_columnconfigure(0, weight=1)
        self._credentials_status = ctk.CTkLabel(
            credentials_row, text="", anchor="w"
        )
        self._credentials_status.grid(row=0, column=0, sticky="ew")
        ctk.CTkButton(
            credentials_row,
            text="Import JSON...",
            width=110,
            command=self._on_import_credentials,
        ).grid(row=0, column=1, padx=(8, 0))
        self.set_credentials_configured(CREDENTIALS_PATH.is_file())
        row += 1

        row = self._add_label(form, row, "Google Drive folder")
        drive_row = ctk.CTkFrame(form, fg_color="transparent")
        drive_row.grid(row=row, column=1, padx=12, pady=8, sticky="ew")
        drive_row.grid_columnconfigure(0, weight=1)
        self._drive_folder_status = ctk.CTkLabel(
            drive_row,
            text=s.last_drive_folder_name or "My Drive",
            anchor="w",
        )
        self._drive_folder_status.grid(row=0, column=0, sticky="ew")
        ctk.CTkButton(
            drive_row,
            text="Choose...",
            width=110,
            command=self._on_choose_drive_folder,
        ).grid(row=0, column=1, padx=(8, 0))
        row += 1

        row = self._add_label(form, row, "Auto-copy link after upload")
        self._auto_copy = ctk.BooleanVar(value=s.auto_copy_link)
        ctk.CTkSwitch(form, text="", variable=self._auto_copy).grid(
            row=row, column=1, padx=12, pady=8, sticky="w"
        )
        row += 1

        row = self._add_label(form, row, "Auto-open link after upload")
        self._auto_open = ctk.BooleanVar(value=s.auto_open_link)
        ctk.CTkSwitch(form, text="", variable=self._auto_open).grid(
            row=row, column=1, padx=12, pady=8, sticky="w"
        )
        row += 1

        row = self._add_label(form, row, "Default local upload folder")
        folder_row = ctk.CTkFrame(form, fg_color="transparent")
        folder_row.grid(row=row, column=1, padx=12, pady=8, sticky="ew")
        folder_row.grid_columnconfigure(0, weight=1)
        self._folder_entry = ctk.CTkEntry(folder_row)
        self._folder_entry.insert(0, s.default_upload_folder)
        self._folder_entry.grid(row=0, column=0, sticky="ew")
        ctk.CTkButton(
            folder_row,
            text="Browse",
            width=80,
            corner_radius=CORNER_RADIUS,
            command=self._browse_folder,
        ).grid(row=0, column=1, padx=(8, 0))
        row += 1

        row = self._add_label(form, row, "Update Beacons automatically")
        self._beacons_enabled = ctk.BooleanVar(value=s.beacons_enabled)
        ctk.CTkSwitch(form, text="", variable=self._beacons_enabled).grid(
            row=row, column=1, padx=12, pady=8, sticky="w"
        )
        row += 1

        row = self._add_label(form, row, "Permanent Drive file ID")
        self._beacons_file_id = ctk.CTkEntry(
            form,
            placeholder_text="Created automatically after the first upload",
        )
        self._beacons_file_id.insert(0, s.beacons_drive_file_id)
        self._beacons_file_id.grid(
            row=row, column=1, padx=12, pady=8, sticky="ew"
        )
        row += 1

        row = self._add_label(form, row, "Beacons public page URL")
        self._beacons_profile_url = ctk.CTkEntry(
            form,
            placeholder_text="https://beacons.ai/your-name",
        )
        self._beacons_profile_url.insert(0, s.beacons_profile_url)
        self._beacons_profile_url.grid(
            row=row, column=1, padx=12, pady=8, sticky="ew"
        )
        row += 1

        row = self._add_label(form, row, "Open Beacons in Chrome after upload")
        self._beacons_open_in_chrome = ctk.BooleanVar(
            value=s.beacons_open_in_chrome
        )
        ctk.CTkSwitch(
            form, text="", variable=self._beacons_open_in_chrome
        ).grid(row=row, column=1, padx=12, pady=8, sticky="w")
        row += 1

        ctk.CTkButton(
            form,
            text="Save Settings",
            corner_radius=CORNER_RADIUS,
            height=BTN_HEIGHT,
            fg_color=ACCENT_RED,
            hover_color=ACCENT_RED_HOVER,
            command=self.save,
        ).grid(row=row, column=0, columnspan=2, padx=12, pady=24)

    def _add_label(self, parent, row: int, text: str) -> int:
        ctk.CTkLabel(parent, text=text, anchor="w").grid(
            row=row, column=0, padx=12, pady=8, sticky="w"
        )
        return row

    def _theme_changed(self, theme: str) -> None:
        self._on_theme_change(theme)

    def set_credentials_configured(self, configured: bool) -> None:
        """Refresh the Google credentials indicator."""
        self._credentials_status.configure(
            text="Configured" if configured else "Required — import your own JSON",
            text_color=ACCENT_GREEN if configured else ACCENT_RED,
        )

    def set_drive_folder_name(self, name: str) -> None:
        """Refresh the selected Google Drive folder label."""
        self._drive_folder_status.configure(text=name or "My Drive")

    def _browse_folder(self) -> None:
        folder = filedialog.askdirectory()
        if folder:
            self._folder_entry.delete(0, "end")
            self._folder_entry.insert(0, folder)

    def save(self) -> None:
        theme = self._theme_var.get()
        theme_changed = theme != self._settings_mgr.settings.theme
        self._settings_mgr.update(
            theme=theme,
            auto_copy_link=self._auto_copy.get(),
            auto_open_link=self._auto_open.get(),
            default_upload_folder=self._folder_entry.get().strip(),
            beacons_enabled=self._beacons_enabled.get(),
            beacons_profile_url=self._beacons_profile_url.get().strip(),
            beacons_drive_file_id=self._beacons_file_id.get().strip(),
            beacons_open_in_chrome=self._beacons_open_in_chrome.get(),
        )
        self._on_save()
        message = "Settings saved."
        if theme_changed:
            message += "\n\nRestart the app to apply the full color theme."
        messagebox.showinfo(APP_NAME, message)


class TutorialPage(ctk.CTkFrame):
    """First-run guide for Google Drive and Beacons configuration."""

    def __init__(
        self,
        master,
        on_open_settings: Callable[[], None],
        on_choose_drive_folder: Callable[[], None],
        **kwargs,
    ) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, padx=PAD, pady=(PAD, 8), sticky="ew")
        ctk.CTkLabel(
            header,
            text="Setup Tutorial",
            font=ctk.CTkFont(size=24, weight="bold"),
            anchor="w",
        ).pack(fill="x")
        ctk.CTkLabel(
            header,
            text="Connect your own Google account, Drive folder, and Beacons page.",
            text_color="gray",
            anchor="w",
        ).pack(fill="x", pady=(4, 0))

        guide = ctk.CTkScrollableFrame(self, corner_radius=CORNER_RADIUS)
        guide.grid(row=1, column=0, padx=PAD, pady=(0, PAD), sticky="nsew")
        guide.grid_columnconfigure(0, weight=1)

        steps = [
            (
                "Create your Google Cloud project",
                "Open Google Cloud, create a project, or select one that belongs "
                "to you. Never share another person's OAuth credentials.",
                "Open Google Cloud",
                lambda: webbrowser.open("https://console.cloud.google.com/projectcreate"),
            ),
            (
                "Enable the Google Drive API",
                "Inside your project, open the Drive API page and click Enable. "
                "The uploader cannot access Drive until this API is enabled.",
                "Enable Drive API",
                lambda: webbrowser.open(
                    "https://console.cloud.google.com/apis/library/drive.googleapis.com"
                ),
            ),
            (
                "Configure Google OAuth",
                "Configure the OAuth consent screen. For a test app, add your "
                "Google account as a test user. Then create an OAuth Client ID "
                "with application type Desktop app and download its JSON file.",
                "Open OAuth Credentials",
                lambda: webbrowser.open(
                    "https://console.cloud.google.com/apis/credentials"
                ),
            ),
            (
                "Import your credentials JSON",
                "Open Settings and click Import JSON. The app validates that it "
                "is a Desktop-app credential file and stores it only on this PC.",
                "Open Settings",
                on_open_settings,
            ),
            (
                "Sign in and choose your Drive folder",
                "Click Choose Drive Folder, complete Google sign-in in your "
                "browser, and select where this user's uploads should be stored.",
                "Choose Drive Folder",
                on_choose_drive_folder,
            ),
            (
                "Connect your Beacons page",
                "In Settings, enable Update Beacons automatically and enter your "
                "own public Beacons URL. Upload once, then put the generated "
                "permanent download URL into your Beacons download button. Later "
                "uploads replace that same Drive file automatically.",
                "Open Beacons",
                lambda: webbrowser.open("https://account.beacons.ai/home"),
            ),
        ]

        for index, (title, body, button_text, command) in enumerate(steps, start=1):
            self._add_step(
                guide,
                row=index - 1,
                number=index,
                title=title,
                body=body,
                button_text=button_text,
                command=command,
            )

        ctk.CTkLabel(
            guide,
            text="Tip: credentials, sign-in tokens, Drive choices, and Beacons "
            "settings remain local to each user on this device.",
            text_color=ACCENT_GREEN,
            wraplength=650,
            justify="left",
        ).grid(row=len(steps), column=0, padx=16, pady=(8, 20), sticky="w")

    def _add_step(
        self,
        parent,
        row: int,
        number: int,
        title: str,
        body: str,
        button_text: str,
        command: Callable[[], None],
    ) -> None:
        card = ctk.CTkFrame(parent, corner_radius=CORNER_RADIUS)
        card.grid(row=row, column=0, padx=8, pady=6, sticky="ew")
        card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            card,
            text=str(number),
            width=38,
            height=38,
            corner_radius=19,
            fg_color=ACCENT_RED if number % 2 else ACCENT_GREEN,
            text_color="white",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).grid(row=0, column=0, rowspan=2, padx=14, pady=14, sticky="n")
        ctk.CTkLabel(
            card,
            text=title,
            anchor="w",
            font=ctk.CTkFont(size=15, weight="bold"),
        ).grid(row=0, column=1, padx=(0, 12), pady=(12, 2), sticky="ew")
        ctk.CTkLabel(
            card,
            text=body,
            anchor="w",
            justify="left",
            wraplength=540,
            text_color="gray",
        ).grid(row=1, column=1, padx=(0, 12), pady=(0, 12), sticky="ew")
        ctk.CTkButton(
            card,
            text=button_text,
            width=145,
            command=command,
            fg_color=ACCENT_GREEN if number % 2 else ACCENT_RED,
            hover_color=ACCENT_GREEN_HOVER if number % 2 else ACCENT_RED_HOVER,
        ).grid(row=0, column=2, rowspan=2, padx=14, pady=14)


class AboutPage(ctk.CTkFrame):
    """About information page."""

    def __init__(self, master, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)

        ctk.CTkLabel(
            self,
            text=APP_NAME,
            font=ctk.CTkFont(size=28, weight="bold"),
        ).pack(pady=(48, 8))

        ctk.CTkLabel(
            self,
            text=f"Version {APP_VERSION}",
            text_color="gray",
        ).pack(pady=4)

        ctk.CTkLabel(
            self,
            text=(
                "Upload 3D printing files to Google Drive,\n"
                "generate public download links, QR codes,\n"
                "and optionally update Beacons.ai."
            ),
            justify="center",
        ).pack(pady=24)

        ctk.CTkLabel(
            self,
            text="Built with Python, CustomTkinter, and Google Drive API",
            text_color="gray",
            font=ctk.CTkFont(size=12),
        ).pack(pady=8)


class FolderPickerDialog(ctk.CTkToplevel):
    """Simple Google Drive folder picker dialog."""

    def __init__(
        self,
        master,
        drive: DriveService,
        current_id: str = "",
        current_name: str = "My Drive",
    ) -> None:
        super().__init__(master)
        self.title("Select Google Drive Folder")
        self.geometry("420x480")
        self.transient(master)
        self.grab_set()

        self._drive = drive
        self._stack: list[tuple[str, str]] = [("", "My Drive")]
        self.selected_id: Optional[str] = None
        self.selected_name = current_name or "My Drive"

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        nav = ctk.CTkFrame(self, fg_color="transparent")
        nav.grid(row=0, column=0, padx=12, pady=12, sticky="ew")

        ctk.CTkButton(
            nav, text="Up", width=60, corner_radius=8, command=self._go_up
        ).pack(side="left")

        self._path_label = ctk.CTkLabel(nav, text="My Drive", anchor="w")
        self._path_label.pack(side="left", padx=12, fill="x", expand=True)

        self._list = ctk.CTkScrollableFrame(self, corner_radius=CORNER_RADIUS)
        self._list.grid(row=1, column=0, padx=12, pady=(0, 12), sticky="nsew")
        self._list.grid_columnconfigure(0, weight=1)

        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.grid(row=2, column=0, padx=12, pady=12, sticky="ew")

        ctk.CTkButton(
            actions,
            text="Select This Folder",
            corner_radius=CORNER_RADIUS,
            fg_color=ACCENT_GREEN,
            hover_color=ACCENT_GREEN_HOVER,
            command=self._select_current,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            actions,
            text="Cancel",
            corner_radius=CORNER_RADIUS,
            command=self.destroy,
        ).pack(side="left")

        self._load_folders()

    @property
    def _current_id(self) -> str:
        return self._stack[-1][0]

    @property
    def _current_name(self) -> str:
        return self._stack[-1][1]

    def _load_folders(self) -> None:
        for w in self._list.winfo_children():
            w.destroy()
        self._path_label.configure(text=self._current_name)

        parent_id = self._current_id or "root"
        try:
            folders = self._drive.list_folders(parent_id=parent_id)
        except DriveError as exc:
            messagebox.showerror(APP_NAME, str(exc), parent=self)
            folders = []

        if not folders:
            ctk.CTkLabel(
                self._list, text="(no subfolders)", text_color="gray"
            ).grid(row=0, column=0, pady=12)

        for idx, folder in enumerate(folders):
            ctk.CTkButton(
                self._list,
                text=f"📁 {folder['name']}",
                anchor="w",
                corner_radius=8,
                fg_color="transparent",
                border_width=1,
                command=lambda f=folder: self._enter(f),
            ).grid(row=idx, column=0, padx=4, pady=2, sticky="ew")

    def _enter(self, folder: dict) -> None:
        self._stack.append((folder["id"], folder["name"]))
        self._load_folders()

    def _go_up(self) -> None:
        if len(self._stack) > 1:
            self._stack.pop()
            self._load_folders()

    def _select_current(self) -> None:
        self.selected_id = self._current_id
        self.selected_name = self._current_name
        self.destroy()


class PrintUploaderApp(ctk.CTk, TkinterDnD.DnDWrapper):
    """Main application window."""

    def __init__(
        self,
        settings_mgr: SettingsManager,
        history_mgr: HistoryManager,
        auth: GoogleAuth,
        uploader: Uploader,
    ) -> None:
        # Load the color palette before Tk creates the root window so the
        # background and every child widget receive the same theme.
        self._apply_theme(settings_mgr.settings.theme)
        super().__init__()
        self.TkdndVersion = TkinterDnD._require(self)

        self._settings_mgr = settings_mgr
        self._history_mgr = history_mgr
        self._auth = auth
        self._uploader = uploader
        self._upload_thread: Optional[threading.Thread] = None

        self._configure_window(settings_mgr.settings)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_pages()
        self._build_menu()
        self._build_status_bar()

        self.upload_page.enable_dnd()
        if CREDENTIALS_PATH.is_file():
            self.show_page("upload")
        else:
            self.show_page("tutorial")
            self.after(350, self._show_first_run_setup)

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _apply_theme(self, theme: str) -> None:
        if theme == "red-green":
            ctk.set_appearance_mode("dark")
            if RED_GREEN_THEME_PATH.exists():
                ctk.set_default_color_theme(str(RED_GREEN_THEME_PATH))
            else:
                logger.warning(
                    "Red-green theme file was not found: %s",
                    RED_GREEN_THEME_PATH,
                )
                ctk.set_default_color_theme("green")
            return

        appearance = theme if theme in {"dark", "light", "system"} else "dark"
        ctk.set_appearance_mode(appearance)
        ctk.set_default_color_theme("blue")

    def _configure_window(self, settings: AppSettings) -> None:
        self.title(APP_NAME)
        if APP_ICON_PATH.exists() and sys.platform == "win32":
            try:
                self.iconbitmap(str(APP_ICON_PATH))
            except Exception as exc:
                logger.warning("Could not set application icon: %s", exc)
        elif APP_ICON_PNG_PATH.exists():
            try:
                self._window_icon = PhotoImage(file=str(APP_ICON_PNG_PATH))
                self.iconphoto(True, self._window_icon)
            except Exception as exc:
                logger.warning("Could not set application icon: %s", exc)
        self.geometry(f"{settings.window_width}x{settings.window_height}")
        self.minsize(720, 560)

    def _build_sidebar(self) -> None:
        sidebar = ctk.CTkFrame(self, width=180, corner_radius=0)
        sidebar.grid(row=0, column=0, rowspan=2, sticky="ns")
        sidebar.grid_rowconfigure(6, weight=1)

        ctk.CTkLabel(
            sidebar,
            text="3D Print\nUploader",
            font=ctk.CTkFont(size=18, weight="bold"),
            justify="center",
        ).grid(row=0, column=0, padx=16, pady=(24, 16))

        buttons = [
            ("Upload", "upload"),
            ("History", "history"),
            ("Settings", "settings"),
            ("Tutorial", "tutorial"),
            ("About", "about"),
        ]
        for idx, (label, page) in enumerate(buttons, start=1):
            ctk.CTkButton(
                sidebar,
                text=label,
                corner_radius=CORNER_RADIUS,
                height=BTN_HEIGHT,
                anchor="w",
                command=lambda p=page: self.show_page(p),
            ).grid(row=idx, column=0, padx=16, pady=4, sticky="ew")

        s = self._settings_mgr.settings
        folder_text = s.last_drive_folder_name or "My Drive"
        self._folder_btn = ctk.CTkButton(
            sidebar,
            text=f"📁 {folder_text[:18]}",
            corner_radius=CORNER_RADIUS,
            height=BTN_HEIGHT,
            fg_color=ACCENT_GREEN,
            hover_color=ACCENT_GREEN_HOVER,
            command=self._pick_drive_folder,
        )
        self._folder_btn.grid(row=7, column=0, padx=16, pady=(8, 24), sticky="ew")

    def _build_pages(self) -> None:
        self._pages: dict[str, ctk.CTkFrame] = {}

        self.upload_page = UploadPage(
            self,
            on_upload=self._start_upload,
            on_browse=self._browse_files,
            on_browse_folder=self._browse_folder,
        )
        self._pages["upload"] = self.upload_page

        self.history_page = HistoryPage(
            self,
            history=self._history_mgr,
            on_refresh=lambda: None,
        )
        self._pages["history"] = self.history_page

        self.settings_page = SettingsPage(
            self,
            settings_mgr=self._settings_mgr,
            on_theme_change=self._apply_theme,
            on_save=self._on_settings_saved,
            on_import_credentials=self._import_google_credentials,
            on_choose_drive_folder=self._pick_drive_folder,
        )
        self._pages["settings"] = self.settings_page

        self.tutorial_page = TutorialPage(
            self,
            on_open_settings=lambda: self.show_page("settings"),
            on_choose_drive_folder=self._pick_drive_folder,
        )
        self._pages["tutorial"] = self.tutorial_page

        self.about_page = AboutPage(self)
        self._pages["about"] = self.about_page

    def _build_menu(self) -> None:
        menu_bar = Menu(self)
        self.configure(menu=menu_bar)

        file_menu = Menu(menu_bar, tearoff=0)
        file_menu.add_command(label="Browse Files...", command=self._browse_files)
        file_menu.add_command(label="Browse Folder...", command=self._browse_folder)
        file_menu.add_command(
            label="Select Drive Folder...", command=self._pick_drive_folder
        )
        file_menu.add_separator()
        file_menu.add_command(label="Sign Out Google", command=self._sign_out)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self._on_close)
        menu_bar.add_cascade(label="File", menu=file_menu)

        view_menu = Menu(menu_bar, tearoff=0)
        view_menu.add_command(
            label="Red & Green", command=lambda: self._set_theme("red-green")
        )
        view_menu.add_separator()
        view_menu.add_command(
            label="Dark Mode", command=lambda: self._set_theme("dark")
        )
        view_menu.add_command(
            label="Light Mode", command=lambda: self._set_theme("light")
        )
        menu_bar.add_cascade(label="View", menu=view_menu)

        help_menu = Menu(menu_bar, tearoff=0)
        help_menu.add_command(
            label="Setup Tutorial", command=lambda: self.show_page("tutorial")
        )
        help_menu.add_command(label="About", command=lambda: self.show_page("about"))
        menu_bar.add_cascade(label="Help", menu=help_menu)

    def _build_status_bar(self) -> None:
        self.status_bar = StatusBar(self)
        self.status_bar.grid(row=1, column=1, sticky="ew")

    def show_page(self, name: str) -> None:
        for page in self._pages.values():
            page.grid_remove()
        page = self._pages.get(name)
        if page:
            page.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
            if name == "history":
                self.history_page.refresh()

    def _set_theme(self, theme: str) -> None:
        self._apply_theme(theme)
        self._settings_mgr.update(theme=theme)

    def _on_settings_saved(self) -> None:
        s = self._settings_mgr.settings
        self._folder_btn.configure(
            text=f"📁 {(s.last_drive_folder_name or 'My Drive')[:18]}"
        )

    def _browse_files(self) -> None:
        s = self._settings_mgr.settings
        initial = s.default_upload_folder or None
        exts = " ".join(f"*{e}" for e in sorted(SUPPORTED_EXTENSIONS))
        path = filedialog.askopenfilename(
            title="Select 3D Print File",
            initialdir=initial,
            filetypes=[
                ("3D Print Files", exts),
                ("All Files", "*.*"),
            ],
        )
        if path:
            self.upload_page.set_selected(Path(path))
            self.show_page("upload")

    def _browse_folder(self) -> None:
        s = self._settings_mgr.settings
        initial = s.default_upload_folder or None
        path = filedialog.askdirectory(
            title="Select Folder to Upload",
            initialdir=initial,
        )
        if path:
            self.upload_page.set_selected(Path(path))
            self.show_page("upload")

    def _show_first_run_setup(self) -> None:
        messagebox.showinfo(
            "Set up 3D Print Uploader",
            "Everything has been reset for a new user.\n\n"
            "Follow the Tutorial page to create and import your own Google "
            "credentials, choose your Drive folder, and connect Beacons.\n\n"
            "No Google or Beacons account is included with the app.",
        )

    def _import_google_credentials(self) -> None:
        source = filedialog.askopenfilename(
            title="Import Google Desktop App Credentials",
            filetypes=[
                ("Google credentials JSON", "*.json"),
                ("All Files", "*.*"),
            ],
        )
        if not source:
            return

        try:
            self._auth.import_client_credentials(Path(source))
        except AuthenticationError as exc:
            messagebox.showerror(APP_NAME, str(exc))
            return

        self.settings_page.set_credentials_configured(True)
        self.status_bar.set_message("Google credentials imported for this user.")
        if messagebox.askyesno(
            APP_NAME,
            "Google credentials imported. Sign in and choose a Drive folder now?",
        ):
            self._pick_drive_folder()

    def _pick_drive_folder(self) -> None:
        try:
            service = self._auth.ensure_authenticated()
            drive = DriveService(service)
        except AuthenticationError as exc:
            messagebox.showerror(APP_NAME, str(exc))
            return

        s = self._settings_mgr.settings
        dialog = FolderPickerDialog(
            self,
            drive,
            current_id=s.last_drive_folder_id,
            current_name=s.last_drive_folder_name,
        )
        self.wait_window(dialog)

        if dialog.selected_id is not None:
            self._settings_mgr.update(
                last_drive_folder_id=dialog.selected_id,
                last_drive_folder_name=dialog.selected_name,
            )
            self._folder_btn.configure(
                text=f"📁 {dialog.selected_name[:18]}"
            )
            self.status_bar.set_message(
                f"Upload folder: {dialog.selected_name}"
            )
            self.settings_page.set_drive_folder_name(dialog.selected_name)

    def _sign_out(self) -> None:
        if messagebox.askyesno(APP_NAME, "Sign out of Google Drive?"):
            self._auth.logout()
            self.status_bar.set_message("Signed out of Google.")

    def _start_upload(self, path: Path) -> None:
        if self._upload_thread and self._upload_thread.is_alive():
            messagebox.showwarning(APP_NAME, "An upload is already in progress.")
            return

        self.status_bar.show_progress(True)
        self.status_bar.set_message("Starting upload...")
        self.upload_page._upload_btn.configure(state="disabled")

        self._upload_thread = threading.Thread(
            target=self._upload_worker,
            args=(path,),
            daemon=True,
        )
        self._upload_thread.start()

    def _upload_worker(self, path: Path) -> None:
        def on_status(msg: str) -> None:
            self.after(0, lambda: self.status_bar.set_message(msg))

        def on_progress(pct: int) -> None:
            self.after(0, lambda: self.status_bar.set_progress(pct))

        try:
            result = self._uploader.upload(
                path, on_status=on_status, on_progress=on_progress
            )
            self.after(0, lambda: self._upload_success(result))
        except UploadError as exc:
            logger.error("Upload error: %s", exc)
            self.after(0, lambda: self._upload_failure(str(exc)))
        except Exception as exc:
            logger.exception("Unexpected upload error")
            self.after(0, lambda: self._upload_failure(str(exc)))

    def _upload_success(self, result: UploadResult) -> None:
        self.status_bar.show_progress(False)
        self.status_bar.set_message(f"Uploaded: {result.filename}")
        self.upload_page.show_result(result)
        self.upload_page.clear_selection()
        self.upload_page._upload_btn.configure(state="disabled")
        messagebox.showinfo(
            APP_NAME,
            f"Successfully uploaded {result.filename}.\n\n"
            f"Download link:\n{result.download_url}",
        )

    def _upload_failure(self, message: str) -> None:
        self.status_bar.show_progress(False)
        self.status_bar.set_message("Upload failed.")
        self.upload_page._upload_btn.configure(state="normal")
        messagebox.showerror(APP_NAME, message)

    def _on_close(self) -> None:
        w, h = self.winfo_width(), self.winfo_height()
        self._settings_mgr.update(window_width=w, window_height=h)
        self.destroy()


def create_app(
    settings_mgr: Optional[SettingsManager] = None,
    history_mgr: Optional[HistoryManager] = None,
    auth: Optional[GoogleAuth] = None,
) -> PrintUploaderApp:
    """Factory to create the main application window."""
    settings_mgr = settings_mgr or SettingsManager()
    history_mgr = history_mgr or HistoryManager()
    auth = auth or GoogleAuth()
    uploader = Uploader(auth, settings_mgr, history_mgr)
    return PrintUploaderApp(settings_mgr, history_mgr, auth, uploader)
