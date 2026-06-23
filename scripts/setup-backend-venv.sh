#!/usr/bin/env bash
# Backend venv: Python 3.12+ + requirements.txt → backend/.venv
# Usage:
#   ./scripts/setup-backend-venv.sh           # vytvoří jen pokud chybí / je neplatné
#   ./scripts/setup-backend-venv.sh --recreate # smazat a znovu

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=lib/backend-venv.sh
source "$REPO_ROOT/scripts/lib/backend-venv.sh"

RECREATE=0
for arg in "$@"; do
    case "$arg" in
        --recreate) RECREATE=1 ;;
        -h|--help)
            echo "Usage: $0 [--recreate]"
            exit 0
            ;;
        *)
            echo "Unknown option: $arg" >&2
            exit 1
            ;;
    esac
done

if [[ "$RECREATE" -eq 1 ]]; then
    ensure_backend_venv --recreate
else
    ensure_backend_venv
fi

echo "==> Django check"
"$BACKEND_PYTHON" "$BACKEND/manage.py" check
echo "OK  backend/.venv ready (activate: source backend/.venv/bin/activate)"
