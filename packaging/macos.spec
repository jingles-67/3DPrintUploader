# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

ROOT = Path(SPECPATH).parent.parent
VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip()

datas = []
binaries = []
hiddenimports = []
for package in ("customtkinter", "tkinterdnd2"):
    package_datas, package_binaries, package_imports = collect_all(package)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_imports

datas += [
    (str(ROOT / "assets" / "icons" / "app_icon.ico"), "assets/icons"),
    (str(ROOT / "assets" / "icons" / "app_icon.png"), "assets/icons"),
    (str(ROOT / "assets" / "themes" / "red_green.json"), "assets/themes"),
    (str(ROOT / "VERSION"), "."),
]

a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="3D Print Uploader",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / "assets" / "icons" / "app_icon.png"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="3D Print Uploader",
)

app = BUNDLE(
    coll,
    name="3D Print Uploader.app",
    icon=str(ROOT / "assets" / "icons" / "app_icon.png"),
    bundle_identifier="nz.co.3dprintingwilliam.uploader",
    info_plist={
        "CFBundleDisplayName": "3D Print Uploader",
        "CFBundleName": "3D Print Uploader",
        "CFBundleShortVersionString": VERSION,
        "CFBundleVersion": VERSION,
        "NSHighResolutionCapable": True,
    },
)
