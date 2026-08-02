@echo off
setlocal

if not exist "%~dp0.venv\Scripts\python.exe" (
    echo Project virtual environment not found.
    exit /b 1
)

"%~dp0.venv\Scripts\python.exe" "%~dp0release.py" --bump patch
exit /b %errorlevel%
