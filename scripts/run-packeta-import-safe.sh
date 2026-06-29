#!/bin/bash
# Denní import Packeta provizí (aktuální měsíc, všechny pobočky). Ochrana proti paralelnímu běhu.
set -euo pipefail

WEBAPP_PATH="${WEBAPP_PATH:-/home/webmajak/webapp}"
LOCK_FILE="/tmp/packeta-import.lock"
LOG_FILE="/var/log/packeta-import.log"
PID_FILE="/tmp/packeta-import.pid"

cleanup() { rm -f "$LOCK_FILE" "$PID_FILE"; }
trap cleanup EXIT

if [ -f "$LOCK_FILE" ] && [ -f "$PID_FILE" ]; then
  OLD_PID=$(cat "$PID_FILE")
  if ps -p "$OLD_PID" > /dev/null 2>&1; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Packeta import už běží (PID $OLD_PID), skip" >> "$LOG_FILE"
    exit 0
  fi
  rm -f "$LOCK_FILE" "$PID_FILE"
fi

touch "$LOCK_FILE"
echo $$ > "$PID_FILE"
echo "$(date '+%Y-%m-%d %H:%M:%S') - Start Packeta import (month, all branches)" >> "$LOG_FILE"

cd "$WEBAPP_PATH" || exit 1
set +e
sudo -u webmajak bash -c "cd '$WEBAPP_PATH' && source venv/bin/activate && \
  python manage.py import_packeta_provize --fetch --period month --all-branches --typ baliky" \
  >> "$LOG_FILE" 2>&1
EXIT_CODE=$?
set -e

if [ "$EXIT_CODE" -eq 0 ]; then
  echo "$(date '+%Y-%m-%d %H:%M:%S') - Hotovo" >> "$LOG_FILE"
else
  echo "$(date '+%Y-%m-%d %H:%M:%S') - Selhalo (exit $EXIT_CODE)" >> "$LOG_FILE"
  exit "$EXIT_CODE"
fi
