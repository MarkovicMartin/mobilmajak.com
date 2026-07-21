#!/bin/bash
# Wrapper – import skladových výdejek (1× denně v noci). Ochrana proti paralelnímu běhu.
set -euo pipefail

ACTOR_DIR="/opt/actor/ACTOR_FINALL_WEB_PRODEJE_ALL"
WEBAPP_PATH="/home/webmajak/webapp"
LOCK_FILE="/tmp/sklad-vydejky-actor.lock"
LOG_FILE="/var/log/sklad-vydejky-actor.log"
PID_FILE="/tmp/sklad-vydejky-actor.pid"
DAYS_BACK="${SKLAD_VYDEJKY_DAYS_BACK:-2}"

cleanup() { rm -f "$LOCK_FILE" "$PID_FILE"; }
trap cleanup EXIT

report_ticket() {
  local kind="$1"
  local message="$2"
  if [ -x "$WEBAPP_PATH/venv/bin/python" ] && [ -f "$WEBAPP_PATH/manage.py" ]; then
    EXPORT_MSG="$message" sudo -u webmajak env \
      IMPORT_MSG="$message" \
      bash -c "cd '$WEBAPP_PATH' && source venv/bin/activate && \
      python manage.py report_sklad_vydejky_import --kind '$kind' --message \"\$IMPORT_MSG\" \
        --from-date '$FROM' --to-date '$TO'" >> "$LOG_FILE" 2>&1 || true
  fi
}

if [ -f "$LOCK_FILE" ] && [ -f "$PID_FILE" ]; then
  OLD_PID=$(cat "$PID_FILE")
  if ps -p "$OLD_PID" > /dev/null 2>&1; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Actor už běží (PID $OLD_PID), skip" >> "$LOG_FILE"
    exit 0
  fi
  rm -f "$LOCK_FILE" "$PID_FILE"
fi

touch "$LOCK_FILE"
echo $$ > "$PID_FILE"
FROM=$(date -d "$DAYS_BACK days ago" +%Y-%m-%d)
TO=$(date +%Y-%m-%d)
echo "$(date '+%Y-%m-%d %H:%M:%S') - Start sklad-vydejky actor ($FROM .. $TO)" >> "$LOG_FILE"

cd "$ACTOR_DIR" || exit 1
if [[ -f "$ACTOR_DIR/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ACTOR_DIR/.env"
  set +a
fi
export SYMPLIO_SCRIPTS_DIR="${SYMPLIO_SCRIPTS_DIR:-/opt/scripts/symplio-shared}"
set +e
HEADLESS=1 CHROME_BIN=/usr/bin/google-chrome /usr/bin/node import-sklad-vydejky.js --from "$FROM" --to "$TO" >> "$LOG_FILE" 2>&1
EXIT_CODE=$?
set -e

if [ "$EXIT_CODE" -eq 0 ]; then
  echo "$(date '+%Y-%m-%d %H:%M:%S') - Hotovo" >> "$LOG_FILE"
elif [ "$EXIT_CODE" -eq 2 ]; then
  TAIL=$(tail -20 "$LOG_FILE" | tr '\n' ' ' | head -c 1500)
  report_ticket warning "$TAIL"
  echo "$(date '+%Y-%m-%d %H:%M:%S') - Hotovo s varováním (exit 2)" >> "$LOG_FILE"
else
  TAIL=$(tail -30 "$LOG_FILE" | tr '\n' ' ' | head -c 1500)
  report_ticket failure "$TAIL"
  echo "$(date '+%Y-%m-%d %H:%M:%S') - Selhalo (exit $EXIT_CODE)" >> "$LOG_FILE"
  exit "$EXIT_CODE"
fi
