#!/bin/bash
# Wrapper – import skladových výdejek (1× denně). Ochrana proti paralelnímu běhu.
set -euo pipefail

ACTOR_DIR="/opt/actor/ACTOR_FINALL_WEB_PRODEJE_ALL"
LOCK_FILE="/tmp/sklad-vydejky-actor.lock"
LOG_FILE="/var/log/sklad-vydejky-actor.log"
PID_FILE="/tmp/sklad-vydejky-actor.pid"

cleanup() { rm -f "$LOCK_FILE" "$PID_FILE"; }
trap cleanup EXIT

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
echo "$(date '+%Y-%m-%d %H:%M:%S') - Start sklad-vydejky actor" >> "$LOG_FILE"

cd "$ACTOR_DIR" || exit 1
TODAY=$(date +%Y-%m-%d)
HEADLESS=1 CHROME_BIN=/usr/bin/google-chrome /usr/bin/node import-sklad-vydejky.js --from "$TODAY" --to "$TODAY" >> "$LOG_FILE" 2>&1

echo "$(date '+%Y-%m-%d %H:%M:%S') - Hotovo" >> "$LOG_FILE"
