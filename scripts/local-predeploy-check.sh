#!/usr/bin/env bash
# Lokální kontrola před deployem (venv, ne systémový python).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
"$REPO_ROOT/scripts/backend-run.sh" manage.py check
echo "OK local predeploy check"
