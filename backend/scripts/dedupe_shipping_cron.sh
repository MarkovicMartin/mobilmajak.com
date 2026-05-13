#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/home/webmajak/webapp"
VENV_PY="$APP_DIR/venv/bin/python"
MANAGE="$APP_DIR/manage.py"
LOG_DIR="$APP_DIR/logs"
LOG_FILE="$LOG_DIR/dedupe_shipping_rows.log"

mkdir -p "$LOG_DIR"
cd "$APP_DIR"

{
  echo "[$(date '+%F %T')] 🔍 Spouštím deduplikaci dopravních řádků..."
  "$VENV_PY" "$MANAGE" dedupe_shipping_rows --apply --skip-checks --verbosity 1 --settings=webapp.settings_production
  echo "[$(date '+%F %T')] ✅ Dokončeno."
} >> "$LOG_FILE" 2>&1


