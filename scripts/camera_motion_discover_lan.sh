#!/bin/bash
# Sken LAN: Hikvision NVR + IP kamery (bez monitoru u NVR)
# Použití: ./scripts/camera_motion_discover_lan.sh [cesta_k_config.json]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CFG="${1:-$ROOT/secrets/camera_motion_prerov.json}"
PY="$ROOT/backend/.venv/bin/python3"
SCRIPT="$ROOT/scripts/camera_motion_gateway.py"

if [ ! -f "$CFG" ]; then
  echo "Chybí $CFG"
  exit 1
fi

exec "$PY" "$SCRIPT" --config "$CFG" --discover-lan
