#!/bin/bash
# Symplio poznámky dokladů – lock, nízká priorita, jeden běh na vlnu (cron sladěný s Packeta).
# Použití: run-symplio-doklad-notes-safe.sh <today|yesterday|audit>
set -euo pipefail

ACTOR_DIR="${SYMPLIO_ACTOR_DIR:-/opt/actor/ACTOR_FINALL_WEB_PRODEJE_ALL}"
LOCK_FILE="${SYMPLIO_DOKLAD_NOTES_LOCK:-/tmp/symplio-doklad-notes.lock}"
LOG_FILE="${SYMPLIO_DOKLAD_NOTES_LOG:-/var/log/symplio-doklad-notes.log}"
PID_FILE="${SYMPLIO_DOKLAD_NOTES_PID:-/tmp/symplio-doklad-notes.pid}"
MODE="${1:-${SYMPLIO_DOKLAD_NOTES_MODE:-today}}"
# Typický běh: 2–8 min (Symplio HTML + UPDATE)
RUN_TIMEOUT="${SYMPLIO_DOKLAD_NOTES_TIMEOUT:-900}"

cleanup() { rm -f "$LOCK_FILE" "$PID_FILE"; }
trap cleanup EXIT

case "$MODE" in
  yesterday|today|audit) ;;
  *)
    echo "Neznámý režim: $MODE (použij yesterday, today nebo audit)" >&2
    exit 2
    ;;
esac

if [ ! -d "$ACTOR_DIR" ]; then
  echo "Chybí ACTOR_DIR: $ACTOR_DIR" >&2
  exit 2
fi

if [ -f "$LOCK_FILE" ] && [ -f "$PID_FILE" ]; then
  OLD_PID=$(cat "$PID_FILE")
  if ps -p "$OLD_PID" > /dev/null 2>&1; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Symplio doklad notes už běží (PID $OLD_PID), skip [$MODE]" >> "$LOG_FILE"
    exit 0
  fi
  rm -f "$LOCK_FILE" "$PID_FILE"
fi

touch "$LOCK_FILE"
echo $$ > "$PID_FILE"
echo "$(date '+%Y-%m-%d %H:%M:%S') - Start Symplio doklad notes [$MODE, timeout ${RUN_TIMEOUT}s]" >> "$LOG_FILE"

set +e
nice -n 10 timeout "${RUN_TIMEOUT}" bash -c "
  set -euo pipefail
  cd '$ACTOR_DIR'
  if [[ -f .env ]]; then
    set -a
    # shellcheck disable=SC1091
    source .env
    set +a
  fi
  node sync-doklad-notes.js --mode '$MODE'
" >> "$LOG_FILE" 2>&1
EXIT_CODE=$?
set -e

if [ "$EXIT_CODE" -eq 0 ]; then
  echo "$(date '+%Y-%m-%d %H:%M:%S') - Hotovo [$MODE]" >> "$LOG_FILE"
elif [ "$EXIT_CODE" -eq 124 ]; then
  echo "$(date '+%Y-%m-%d %H:%M:%S') - Timeout ${RUN_TIMEOUT}s [$MODE]" >> "$LOG_FILE"
else
  echo "$(date '+%Y-%m-%d %H:%M:%S') - Selhalo (exit $EXIT_CODE) [$MODE]" >> "$LOG_FILE"
fi
exit "$EXIT_CODE"
