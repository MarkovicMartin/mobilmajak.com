#!/bin/bash
# Fio import nákladů – lock, timeout, jeden běh najednou.
# Cron: 22:30 denně (po Packeta vlně) – viz scripts/install-finance-cron.sh
# Použití: run-finance-import-safe.sh [--days N]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=finance-webapp-env.sh
source "$SCRIPT_DIR/finance-webapp-env.sh"
finance_resolve_webapp "$SCRIPT_DIR"

LOCK_FILE="${FINANCE_IMPORT_LOCK:-/tmp/finance-fio-import.lock}"
LOG_FILE="${FINANCE_IMPORT_LOG:-/var/log/finance-fio-import.log}"
PID_FILE="${FINANCE_IMPORT_PID:-/tmp/finance-fio-import.pid}"
RUN_TIMEOUT="${FINANCE_IMPORT_TIMEOUT:-600}"
DAYS="${FINANCE_IMPORT_DAYS:-3}"

# Přepíše DAYS z argumentu --days
while [ $# -gt 0 ]; do
  case "$1" in
    --days)
      DAYS="${2:-3}"
      shift 2
      ;;
    *)
      shift
      ;;
  esac
done

cleanup() { rm -f "$LOCK_FILE" "$PID_FILE"; }
trap cleanup EXIT

if [ -f "$LOCK_FILE" ] && [ -f "$PID_FILE" ]; then
  OLD_PID=$(cat "$PID_FILE")
  if ps -p "$OLD_PID" > /dev/null 2>&1; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Fio import už běží (PID $OLD_PID), skip" >> "$LOG_FILE"
    exit 0
  fi
  rm -f "$LOCK_FILE" "$PID_FILE"
fi

MANAGE_CMD=$(finance_manage_cmd "import_fio_naklady --days '$DAYS'")

touch "$LOCK_FILE"
echo $$ > "$PID_FILE"
echo "$(date '+%Y-%m-%d %H:%M:%S') - Start Fio import (days=$DAYS, timeout ${RUN_TIMEOUT}s)" >> "$LOG_FILE"

set +e
nice -n 10 timeout "${RUN_TIMEOUT}" bash -c "
  set -euo pipefail
  $MANAGE_CMD
" >> "$LOG_FILE" 2>&1
EXIT_CODE=$?
set -e

if [ "$EXIT_CODE" -eq 0 ]; then
  echo "$(date '+%Y-%m-%d %H:%M:%S') - Hotovo Fio import" >> "$LOG_FILE"
elif [ "$EXIT_CODE" -eq 124 ]; then
  echo "$(date '+%Y-%m-%d %H:%M:%S') - Timeout ${RUN_TIMEOUT}s" >> "$LOG_FILE"
else
  echo "$(date '+%Y-%m-%d %H:%M:%S') - Selhalo (exit $EXIT_CODE)" >> "$LOG_FILE"
fi
exit "$EXIT_CODE"
