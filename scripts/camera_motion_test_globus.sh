#!/bin/bash
# Rychlý test pilotu Globus (čte secrets/camera_motion_globus.json)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CFG="$ROOT/secrets/camera_motion_globus.json"
PY="$ROOT/backend/.venv/bin/python3"
SCRIPT="$ROOT/scripts/camera_motion_gateway.py"

if [ ! -f "$CFG" ]; then
  echo "Chybí $CFG"
  echo "Zkopírujte: cp secrets/camera_motion_globus.example.json secrets/camera_motion_globus.json"
  exit 1
fi

MODE="${1:-motion}"
case "$MODE" in
  isapi)  exec "$PY" "$SCRIPT" --config "$CFG" --test-isapi ;;
  motion) exec "$PY" "$SCRIPT" --config "$CFG" --test-motion "${2:-true}" ;;
  *) echo "Použití: $0 isapi | $0 motion [true|false]"; exit 1 ;;
esac
