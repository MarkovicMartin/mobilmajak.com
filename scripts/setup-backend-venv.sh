#!/usr/bin/env bash
# Recreate backend/.venv with Python 3.12+ (required for PEP 604 types in coaching/, plans/, …)
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND="$REPO_ROOT/backend"
MIN_MAJOR=3
MIN_MINOR=12

pick_python() {
    if command -v uv >/dev/null 2>&1; then
        uv python install "$MIN_MAJOR.$MIN_MINOR" >/dev/null 2>&1 || true
        uv python find "$MIN_MAJOR.$MIN_MINOR"
        return
    fi
    for py in python3.12 python3.13 python3; do
        if command -v "$py" >/dev/null 2>&1; then
            ver="$("$py" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
            major="${ver%%.*}"
            minor="${ver#*.}"
            if [ "$major" -gt "$MIN_MAJOR" ] || { [ "$major" -eq "$MIN_MAJOR" ] && [ "$minor" -ge "$MIN_MINOR" ]; }; then
                command -v "$py"
                return
            fi
        fi
    done
    echo "ERROR: Python $MIN_MAJOR.$MIN_MINOR+ not found. Install via https://www.python.org/downloads/ or: curl -LsSf https://astral.sh/uv/install.sh | sh" >&2
    exit 1
}

PYTHON="$(pick_python)"
echo "==> Using $PYTHON ($("$PYTHON" --version))"

rm -rf "$BACKEND/.venv"
if command -v uv >/dev/null 2>&1; then
    uv venv "$BACKEND/.venv" --python "$PYTHON"
    uv pip install -r "$BACKEND/requirements.txt" --python "$BACKEND/.venv/bin/python"
else
    "$PYTHON" -m venv "$BACKEND/.venv"
    "$BACKEND/.venv/bin/pip" install -q --upgrade pip
    "$BACKEND/.venv/bin/pip" install -r "$BACKEND/requirements.txt"
fi

echo "==> Django check"
"$BACKEND/.venv/bin/python" "$BACKEND/manage.py" check
echo "OK  backend/.venv ready (activate: source backend/.venv/bin/activate)"
