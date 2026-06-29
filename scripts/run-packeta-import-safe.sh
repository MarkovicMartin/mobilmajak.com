#!/bin/bash
# Import Packeta provizí – 3× denně (month v noci, recent poledne/večer). Ochrana proti paralelnímu běhu.
set -euo pipefail

WEBAPP_PATH="${WEBAPP_PATH:-/home/webmajak/webapp}"
LOCK_FILE="${PACKETA_LOCK_FILE:-/tmp/packeta-import.lock}"
LOG_FILE="${PACKETA_LOG_FILE:-/var/log/packeta-import.log}"
PID_FILE="${PACKETA_PID_FILE:-/tmp/packeta-import.pid}"
MODE="${1:-${PACKETA_IMPORT_MODE:-month}}"

cleanup() { rm -f "$LOCK_FILE" "$PID_FILE"; }
trap cleanup EXIT

case "$MODE" in
  month)
    IMPORT_CMD="python manage.py import_packeta_provize --fetch --period month --all-branches --typ baliky"
    MODE_LABEL="month (celý měsíc, všechny pobočky)"
    ;;
  recent)
    DAYS="${PACKETA_RECENT_DAYS:-3}"
    IMPORT_CMD="python manage.py import_packeta_provize --fetch --period days --days ${DAYS} --all-branches --typ baliky"
    MODE_LABEL="recent (poslední ${DAYS} dny, všechny pobočky)"
    ;;
  *)
    echo "Neznámý režim: $MODE (použij month nebo recent)" >&2
    exit 2
    ;;
esac

if [ -f "$LOCK_FILE" ] && [ -f "$PID_FILE" ]; then
  OLD_PID=$(cat "$PID_FILE")
  if ps -p "$OLD_PID" > /dev/null 2>&1; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Packeta import už běží (PID $OLD_PID), skip [$MODE]" >> "$LOG_FILE"
    exit 0
  fi
  rm -f "$LOCK_FILE" "$PID_FILE"
fi

touch "$LOCK_FILE"
echo $$ > "$PID_FILE"
echo "$(date '+%Y-%m-%d %H:%M:%S') - Start Packeta import [$MODE_LABEL]" >> "$LOG_FILE"

cd "$WEBAPP_PATH" || exit 1
set +e
sudo -u webmajak bash -c "cd '$WEBAPP_PATH' && source venv/bin/activate && ${IMPORT_CMD}" \
  >> "$LOG_FILE" 2>&1
EXIT_CODE=$?
set -e

if [ "$EXIT_CODE" -eq 0 ]; then
  echo "$(date '+%Y-%m-%d %H:%M:%S') - Hotovo [$MODE]" >> "$LOG_FILE"
else
  echo "$(date '+%Y-%m-%d %H:%M:%S') - Selhalo (exit $EXIT_CODE) [$MODE]" >> "$LOG_FILE"
  exit "$EXIT_CODE"
fi
