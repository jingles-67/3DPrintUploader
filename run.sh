#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$project_dir"

if ! command -v python3 >/dev/null 2>&1; then
    echo "Python 3.12 or newer is required."
    exit 1
fi

if [[ ! -x ".venv/bin/python" ]]; then
    python3 -m venv .venv
fi

.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
exec .venv/bin/python main.py
