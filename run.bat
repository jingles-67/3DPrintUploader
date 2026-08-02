@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment...
    "C:\Users\wdj99\AppData\Local\Programs\Python\Python314\python.exe" -m venv .venv
    .venv\Scripts\python.exe -m pip install -r requirements.txt
)
.venv\Scripts\python.exe main.py
