#!/usr/bin/env bash
# Spustí příkaz v backend/.venv (Python 3.12+). Venv se vytvoří automaticky.
# Usage:
#   ./scripts/backend-run.sh manage.py check
#   ./scripts/backend-run.sh manage.py test tasks
#   ./scripts/backend-run.sh -c "import django; print(django.VERSION)"

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=lib/backend-venv.sh
source "$REPO_ROOT/scripts/lib/backend-venv.sh"

if [[ $# -lt 1 ]]; then
    echo "Usage: $0 <command> [args...]" >&2
    echo "Example: $0 manage.py check" >&2
    exit 1
fi

ensure_backend_venv
cd "$BACKEND"
exec "$BACKEND_PYTHON" "$@"
