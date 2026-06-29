#!/bin/bash
# Rychlý test pilotu Vsetín (čte secrets/camera_motion_vsetin.json)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CFG="$ROOT/secrets/camera_motion_vsetin.json"
PY="$ROOT/backend/.venv/bin/python3"
SCRIPT="$ROOT/scripts/camera_motion_gateway.py"

if [ ! -f "$CFG" ]; then
  echo "Chybí $CFG"
  echo "Zkopírujte: cp scripts/vsetin-gateway/config.example.json secrets/camera_motion_vsetin.json a doplňte"
  exit 1
fi

MODE="${1:-motion}"
case "$MODE" in
  isapi)  exec "$PY" "$SCRIPT" --config "$CFG" --test-isapi ;;
  motion) exec "$PY" "$SCRIPT" --config "$CFG" --test-motion "${2:-true}" ;;
  discover) exec "$PY" "$SCRIPT" --config "$CFG" --discover-lan ;;
  *) echo "Použití: $0 isapi | $0 motion [true|false] | $0 discover"; exit 1 ;;
esac
