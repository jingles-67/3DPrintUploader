"""Entry point for the 3D Print Uploader application."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _relaunch_with_venv_if_needed() -> None:
    """Re-launch using the project venv when deps are missing."""
    try:
        import customtkinter  # noqa: F401
        return
    except ImportError:
        pass

    app_dir = Path(__file__).resolve().parent
    if sys.platform == "win32":
        venv_python = app_dir / ".venv" / "Scripts" / "python.exe"
    else:
        venv_python = app_dir / ".venv" / "bin" / "python"
    if venv_python.exists() and Path(sys.executable).resolve() != venv_python.resolve():
        os.execv(str(venv_python), [str(venv_python), str(app_dir / "main.py"), *sys.argv[1:]])


_relaunch_with_venv_if_needed()


def main() -> None:
    """Launch the application."""
    from utils import APP_NAME, ensure_directories, setup_logging

    logger = setup_logging()
    ensure_directories()
    logger.info("Starting %s", APP_NAME)

    try:
        from gui import create_app

        app = create_app()
        app.mainloop()
    except ImportError as exc:
        logger.critical("Missing dependency: %s (python: %s)", exc, sys.executable)
        venv_command = (
            r".venv\Scripts\python.exe main.py"
            if sys.platform == "win32"
            else ".venv/bin/python main.py"
        )
        launcher = "run.bat" if sys.platform == "win32" else "run.sh"
        print(
            f"Error: {exc}\n"
            f"Python: {sys.executable}\n\n"
            "Dependencies are installed in the project venv. Run with:\n"
            f"  {venv_command}\n"
            f"Or use {launcher}\n\n"
            "To install into the current Python:\n"
            "  pip install -r requirements.txt",
            file=sys.stderr,
        )
        sys.exit(1)
    except Exception as exc:
        logger.exception("Fatal error: %s", exc)
        sys.exit(1)

    logger.info("Application closed.")


if __name__ == "__main__":
    main()
