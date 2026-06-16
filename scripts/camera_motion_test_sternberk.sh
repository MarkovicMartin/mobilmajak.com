#!/bin/bash
# Rychlý test pilotu Šternberk (čte secrets/camera_motion_sternberk.json)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CFG="$ROOT/secrets/camera_motion_sternberk.json"
PY="$ROOT/backend/.venv/bin/python3"
SCRIPT="$ROOT/scripts/camera_motion_gateway.py"

if [ ! -f "$CFG" ]; then
  echo "Chybí $CFG"
  echo "Zkopírujte: cp scripts/sternberk-gateway/config.example.json secrets/camera_motion_sternberk.json a doplňte"
  exit 1
fi

MODE="${1:-motion}"
case "$MODE" in
  isapi)  exec "$PY" "$SCRIPT" --config "$CFG" --test-isapi ;;
  motion) exec "$PY" "$SCRIPT" --config "$CFG" --test-motion "${2:-true}" ;;
  *) echo "Použití: $0 isapi | $0 motion [true|false]"; exit 1 ;;
esac
