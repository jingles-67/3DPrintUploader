"""Create a credential-free source archive for all other platforms."""

from __future__ import annotations

import argparse
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parent.parent
PRIVATE_NAMES = {
    "app.log",
    "config.json",
    "credentials.json",
    "history.json",
    "token.json",
}
EXCLUDED_PARTS = {
    ".git",
    ".github",
    ".idea",
    ".venv",
    ".vscode",
    "__pycache__",
    "build",
    "dist",
    "publish",
    "temp",
}
EXCLUDED_SUFFIXES = {".pyc", ".pyo"}


def included(path: Path) -> bool:
    relative = path.relative_to(ROOT)
    excluded_directory = any(
        part in EXCLUDED_PARTS or part.startswith(("build-", "dist-"))
        for part in relative.parts
    )
    return (
        path.is_file()
        and path.name not in PRIVATE_NAMES
        and path.suffix.lower() not in EXCLUDED_SUFFIXES
        and not excluded_directory
    )


def build_archive(output_dir: Path) -> Path:
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    folder_name = f"3D-Print-Uploader-{version}-Source"
    output_dir.mkdir(parents=True, exist_ok=True)
    destination = output_dir / f"{folder_name}.zip"
    with ZipFile(destination, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for source in sorted(ROOT.rglob("*")):
            if included(source):
                archive.write(source, Path(folder_name) / source.relative_to(ROOT))
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "output_dir",
        nargs="?",
        type=Path,
        default=ROOT / "dist" / "release-assets",
    )
    args = parser.parse_args()
    print(build_archive(args.output_dir))


if __name__ == "__main__":
    main()
