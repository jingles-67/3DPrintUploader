"""Increment the app version and build matching platform packages."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VERSION_PATH = ROOT / "VERSION"
VERSION_INFO_PATH = ROOT / "version_info.txt"
VERSION_PATTERN = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


def parse_version(value: str) -> tuple[int, int, int]:
    """Parse a three-part semantic version."""
    match = VERSION_PATTERN.fullmatch(value.strip())
    if not match:
        raise ValueError(f"Invalid version: {value!r}; expected MAJOR.MINOR.PATCH")
    return tuple(int(part) for part in match.groups())  # type: ignore[return-value]


def bump_version(value: str, part: str = "patch") -> str:
    """Increment one semantic-version component and reset lower components."""
    major, minor, patch = parse_version(value)
    if part == "major":
        major, minor, patch = major + 1, 0, 0
    elif part == "minor":
        minor, patch = minor + 1, 0
    elif part == "patch":
        patch += 1
    else:
        raise ValueError(f"Unknown version component: {part}")
    return f"{major}.{minor}.{patch}"


def render_version_info(version: str) -> str:
    """Create the PyInstaller Windows version-resource definition."""
    major, minor, patch = parse_version(version)
    numeric = f"{major}, {minor}, {patch}, 0"
    return f"""VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({numeric}),
    prodvers=({numeric}),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        '040904B0',
        [
          StringStruct('CompanyName', '3D Printing William'),
          StringStruct('FileDescription', '3D Print Uploader'),
          StringStruct('FileVersion', '{version}'),
          StringStruct('InternalName', '3D Print Uploader'),
          StringStruct('OriginalFilename', '3D Print Uploader.exe'),
          StringStruct('ProductName', '3D Print Uploader'),
          StringStruct('ProductVersion', '{version}')
        ]
      )
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""


def write_version_files(version: str) -> None:
    """Update both human-readable and Windows version resources."""
    parse_version(version)
    VERSION_PATH.write_text(f"{version}\n", encoding="utf-8")
    VERSION_INFO_PATH.write_text(render_version_info(version), encoding="utf-8")


def find_makensis() -> Path:
    """Locate the installed NSIS compiler."""
    candidates = (
        Path(r"C:\Program Files (x86)\NSIS\makensis.exe"),
        Path(r"C:\Program Files\NSIS\makensis.exe"),
        Path.home() / "AppData" / "Local" / "Programs" / "NSIS" / "makensis.exe",
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate

    located = shutil.which("makensis")
    if located:
        return Path(located)
    raise FileNotFoundError("NSIS compiler not found. Install NSIS 3 first.")


def build_release(version: str) -> None:
    """Build native packages for the current operating system."""
    if sys.platform == "darwin":
        subprocess.run(
            ["bash", str(ROOT / "packaging" / "build_macos.sh")],
            cwd=ROOT,
            check=True,
        )
        return

    if sys.platform.startswith("linux"):
        subprocess.run(
            ["bash", str(ROOT / "packaging" / "build_linux.sh")],
            cwd=ROOT,
            check=True,
        )
        return

    subprocess.run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            "3D Print Uploader.spec",
        ],
        cwd=ROOT,
        check=True,
    )
    subprocess.run(
        [
            str(find_makensis()),
            "/V3",
            f"/DAPP_VERSION={version}",
            f"/DAPP_VERSION_4={version}.0",
            str(ROOT / "installer" / "3DPrintUploader.nsi"),
        ],
        cwd=ROOT,
        check=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--bump",
        choices=("patch", "minor", "major"),
        default="patch",
        help="Version component to increment (default: patch).",
    )
    parser.add_argument(
        "--no-build",
        action="store_true",
        help="Only update version files; do not build artifacts.",
    )
    args = parser.parse_args()

    current = VERSION_PATH.read_text(encoding="utf-8").strip()
    version = bump_version(current, args.bump)
    write_version_files(version)
    print(f"Version updated: {current} -> {version}")

    if not args.no_build:
        build_release(version)
        print(f"Release {version} built successfully.")


if __name__ == "__main__":
    main()
