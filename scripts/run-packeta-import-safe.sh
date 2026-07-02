#!/bin/bash
# Packeta import – izolovaný běh (lock, nízká priorita). Nové řádky get_or_create, existující se nepřepisují.
set -euo pipefail

WEBAPP_PATH="${WEBAPP_PATH:-/home/webmajak/webapp}"
LOCK_FILE="${PACKETA_LOCK_FILE:-/tmp/packeta-import.lock}"
LOG_FILE="${PACKETA_LOG_FILE:-/var/log/packeta-import.log}"
PID_FILE="${PACKETA_PID_FILE:-/tmp/packeta-import.pid}"
MODE="${1:-${PACKETA_IMPORT_MODE:-today}}"

cleanup() { rm -f "$LOCK_FILE" "$PID_FILE"; }
trap cleanup EXIT

case "$MODE" in
  yesterday)
    IMPORT_CMD="nice -n 10 python manage.py import_packeta_provize --fetch --period yesterday --all-branches --typ baliky"
    MODE_LABEL="yesterday (včera, 6 poboček)"
    ;;
  today)
    IMPORT_CMD="nice -n 10 python manage.py import_packeta_provize --fetch --period today --all-branches --typ baliky"
    MODE_LABEL="today (dnes, doplnění nových)"
    ;;
  audit)
    DAYS="${PACKETA_AUDIT_DAYS:-7}"
    IMPORT_CMD="nice -n 10 python manage.py import_packeta_provize --fetch --period days --days ${DAYS} --all-branches --typ baliky"
    MODE_LABEL="audit (poslední ${DAYS} dní, reconciliace)"
    ;;
  *)
    echo "Neznámý režim: $MODE (použij yesterday, today nebo audit)" >&2
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
sudo -u webmajak bash -c "cd '$WEBAPP_PATH' && source venv/bin/activate && export DJANGO_SETTINGS_MODULE=webapp.settings_production && ${IMPORT_CMD}" \
  >> "$LOG_FILE" 2>&1
EXIT_CODE=$?
set -e

if [ "$EXIT_CODE" -eq 0 ]; then
  echo "$(date '+%Y-%m-%d %H:%M:%S') - Hotovo [$MODE]" >> "$LOG_FILE"
else
  echo "$(date '+%Y-%m-%d %H:%M:%S') - Selhalo (exit $EXIT_CODE) [$MODE] – opraví další běh" >> "$LOG_FILE"
  exit "$EXIT_CODE"
fi
