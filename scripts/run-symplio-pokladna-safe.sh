#!/bin/bash
# Symplio historie pokladny – lock + timeout wrapper.
# Cron: denně 8:30–21:00 (DAYS=1) + full catch-up 22:00 – viz install-finance-cron.sh.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=finance-webapp-env.sh
source "$SCRIPT_DIR/finance-webapp-env.sh"
finance_resolve_webapp "$SCRIPT_DIR"

ACTOR_DIR="${SYMPLIO_POKLADNA_DIR:-$SCRIPT_DIR/symplio-pokladna-historie}"
LOCK_FILE="${SYMPLIO_POKLADNA_LOCK:-/tmp/symplio-pokladna.lock}"
LOG_FILE="${SYMPLIO_POKLADNA_LOG:-/var/log/symplio-pokladna.log}"
PID_FILE="${SYMPLIO_POKLADNA_PID:-/tmp/symplio-pokladna.pid}"
RUN_TIMEOUT="${SYMPLIO_POKLADNA_TIMEOUT:-900}"
REPORTS_DIR="$ACTOR_DIR/reports"

cleanup() { rm -f "$LOCK_FILE" "$PID_FILE"; }
trap cleanup EXIT

if [ ! -d "$ACTOR_DIR" ]; then
  echo "$(date '+%Y-%m-%d %H:%M:%S') - Chybí ACTOR_DIR: $ACTOR_DIR" >> "$LOG_FILE"
  exit 2
fi

if [ -f "$LOCK_FILE" ] && [ -f "$PID_FILE" ]; then
  OLD_PID=$(cat "$PID_FILE")
  if ps -p "$OLD_PID" > /dev/null 2>&1; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Symplio pokladna už běží (PID $OLD_PID), skip" >> "$LOG_FILE"
    exit 0
  fi
  rm -f "$LOCK_FILE" "$PID_FILE"
fi

IMPORT_CMD=$(finance_manage_cmd "import_symplio_pokladna --input-dir '$REPORTS_DIR'")

touch "$LOCK_FILE"
echo $$ > "$PID_FILE"
echo "$(date '+%Y-%m-%d %H:%M:%S') - Start Symplio pokladna historie [timeout ${RUN_TIMEOUT}s]" >> "$LOG_FILE"

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
  if [[ ! -d node_modules ]]; then
    npm install --omit=dev
  fi
  node fetch-pokladna-xlsx.js
  if compgen -G 'reports/*.xlsx' > /dev/null; then
    $IMPORT_CMD
  else
    echo 'Žádné XLSX v reports/ – import přeskočen'
  fi
" >> "$LOG_FILE" 2>&1
EXIT_CODE=$?
set -e

if [ "$EXIT_CODE" -eq 0 ]; then
  echo "$(date '+%Y-%m-%d %H:%M:%S') - Hotovo Symplio pokladna" >> "$LOG_FILE"
elif [ "$EXIT_CODE" -eq 124 ]; then
  echo "$(date '+%Y-%m-%d %H:%M:%S') - Timeout ${RUN_TIMEOUT}s" >> "$LOG_FILE"
else
  echo "$(date '+%Y-%m-%d %H:%M:%S') - Selhalo (exit $EXIT_CODE)" >> "$LOG_FILE"
fi
exit "$EXIT_CODE"
