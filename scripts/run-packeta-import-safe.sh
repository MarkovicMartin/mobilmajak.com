#!/bin/bash
# Packeta import – lock, nízká priorita, jedna pobočka na běh (cron je rozkouskovaný).
# Použití: run-packeta-import-safe.sh <today|yesterday|audit> [prodejna_id 1-6]
set -euo pipefail

WEBAPP_PATH="${WEBAPP_PATH:-/home/webmajak/webapp}"
LOCK_FILE="${PACKETA_LOCK_FILE:-/tmp/packeta-import.lock}"
LOG_FILE="${PACKETA_LOG_FILE:-/var/log/packeta-import.log}"
PID_FILE="${PACKETA_PID_FILE:-/tmp/packeta-import.pid}"
MODE="${1:-${PACKETA_IMPORT_MODE:-today}}"
PRODEJNA_ID="${2:-${PACKETA_PRODEJNA_ID:-}}"
# Typický běh 1 pobočka / 1 den: 3–6 min; audit 7 dní: 8–15 min. Bezpečnostní strop:
RUN_TIMEOUT="${PACKETA_RUN_TIMEOUT:-600}"

cleanup() { rm -f "$LOCK_FILE" "$PID_FILE"; }
trap cleanup EXIT

if [ -n "$PRODEJNA_ID" ]; then
  if ! [[ "$PRODEJNA_ID" =~ ^[1-6]$ ]]; then
    echo "prodejna_id musí být 1–6, dostal: $PRODEJNA_ID" >&2
    exit 2
  fi
  PRODEJNA_ARGS="--prodejna-id ${PRODEJNA_ID}"
  BACKFILL_PRODEJNA="--prodejna-id ${PRODEJNA_ID}"
  STORE_LABEL="prodejna ${PRODEJNA_ID}"
else
  PRODEJNA_ARGS="--all-branches"
  BACKFILL_PRODEJNA=""
  STORE_LABEL="všechny pobočky"
fi

case "$MODE" in
  yesterday)
    IMPORT_CMD="nice -n 10 timeout ${RUN_TIMEOUT} python manage.py import_packeta_provize --fetch --period yesterday ${PRODEJNA_ARGS} --typ baliky"
    BACKFILL_FROM="$(date -d '2 days ago' +%Y-%m-%d 2>/dev/null || date -v-2d +%Y-%m-%d)"
    MODE_LABEL="yesterday (${STORE_LABEL})"
    ;;
  today)
    IMPORT_CMD="nice -n 10 timeout ${RUN_TIMEOUT} python manage.py import_packeta_provize --fetch --period today ${PRODEJNA_ARGS} --typ baliky"
    BACKFILL_FROM="$(date -d '1 day ago' +%Y-%m-%d 2>/dev/null || date -v-1d +%Y-%m-%d)"
    MODE_LABEL="today (${STORE_LABEL})"
    ;;
  audit)
    DAYS="${PACKETA_AUDIT_DAYS:-7}"
    IMPORT_CMD="nice -n 10 timeout ${RUN_TIMEOUT} python manage.py import_packeta_provize --fetch --period days --days ${DAYS} ${PRODEJNA_ARGS} --typ baliky"
    BACKFILL_FROM="$(date -d "${DAYS} days ago" +%Y-%m-%d 2>/dev/null || date -v-${DAYS}d +%Y-%m-%d)"
    MODE_LABEL="audit ${DAYS}d (${STORE_LABEL})"
    ;;
  *)
    echo "Neznámý režim: $MODE (použij yesterday, today nebo audit)" >&2
    exit 2
    ;;
esac

BACKFILL_CMD="nice -n 10 python manage.py backfill_packeta_prodejci --force --date-from ${BACKFILL_FROM} ${BACKFILL_PRODEJNA}"

if [ -f "$LOCK_FILE" ] && [ -f "$PID_FILE" ]; then
  OLD_PID=$(cat "$PID_FILE")
  if ps -p "$OLD_PID" > /dev/null 2>&1; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Packeta import už běží (PID $OLD_PID), skip [$MODE ${PRODEJNA_ID:-*}]" >> "$LOG_FILE"
    exit 0
  fi
  rm -f "$LOCK_FILE" "$PID_FILE"
fi

touch "$LOCK_FILE"
echo $$ > "$PID_FILE"
echo "$(date '+%Y-%m-%d %H:%M:%S') - Start Packeta import [$MODE_LABEL, timeout ${RUN_TIMEOUT}s]" >> "$LOG_FILE"

cd "$WEBAPP_PATH" || exit 1
set +e
sudo -u webmajak bash -c "cd '$WEBAPP_PATH' && source venv/bin/activate && export DJANGO_SETTINGS_MODULE=webapp.settings_production && ${IMPORT_CMD}" \
  >> "$LOG_FILE" 2>&1
EXIT_CODE=$?
set -e

if [ "$EXIT_CODE" -eq 0 ]; then
  echo "$(date '+%Y-%m-%d %H:%M:%S') - Import OK, backfill od ${BACKFILL_FROM} [$MODE ${PRODEJNA_ID:-*}]" >> "$LOG_FILE"
  set +e
  sudo -u webmajak bash -c "cd '$WEBAPP_PATH' && source venv/bin/activate && export DJANGO_SETTINGS_MODULE=webapp.settings_production && ${BACKFILL_CMD}" \
    >> "$LOG_FILE" 2>&1
  BACKFILL_CODE=$?
  set -e
  if [ "$BACKFILL_CODE" -ne 0 ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Backfill selhal (exit $BACKFILL_CODE) [$MODE ${PRODEJNA_ID:-*}]" >> "$LOG_FILE"
    exit "$BACKFILL_CODE"
  fi
  echo "$(date '+%Y-%m-%d %H:%M:%S') - Hotovo [$MODE ${PRODEJNA_ID:-*}]" >> "$LOG_FILE"
else
  if [ "$EXIT_CODE" -eq 124 ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Timeout ${RUN_TIMEOUT}s [$MODE ${PRODEJNA_ID:-*}]" >> "$LOG_FILE"
  else
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Selhalo (exit $EXIT_CODE) [$MODE ${PRODEJNA_ID:-*}]" >> "$LOG_FILE"
  fi
  exit "$EXIT_CODE"
fi
