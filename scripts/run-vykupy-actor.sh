#!/bin/bash

# WRAPPER PRO VYKUPY ACTOR - ochrana proti paralelnímu běhu

ACTOR_DIR="/opt/actor/ACTOR_VYKUPY"
LOCK_FILE="/tmp/vykupy-actor.lock"
LOG_FILE="/var/log/vykupy-actor.log"
PID_FILE="/tmp/vykupy-actor.pid"
SELENIUM_CLEANUP="${SELENIUM_CLEANUP:-/opt/scripts/selenium-chrome-cleanup.sh}"

cleanup() {
    if [ -x "$SELENIUM_CLEANUP" ]; then
        "$SELENIUM_CLEANUP" --orphans-only >> "$LOG_FILE" 2>&1 || true
    fi
    rm -f "$LOCK_FILE" "$PID_FILE"
}
trap cleanup EXIT

if [ -f "$LOCK_FILE" ]; then
    if [ -f "$PID_FILE" ]; then
        OLD_PID=$(cat "$PID_FILE")
        if ps -p "$OLD_PID" > /dev/null 2>&1; then
            echo "$(date '+%Y-%m-%d %H:%M:%S') - ⏭️  Actor již běží (PID: $OLD_PID), přeskakuji tento běh" >> "$LOG_FILE"
            exit 0
        else
            echo "$(date '+%Y-%m-%d %H:%M:%S') - 🧹 Mrtvý lock file odstraněn" >> "$LOG_FILE"
            rm -f "$LOCK_FILE" "$PID_FILE"
        fi
    else
        rm -f "$LOCK_FILE"
    fi
fi

touch "$LOCK_FILE"
echo $$ > "$PID_FILE"

echo "$(date '+%Y-%m-%d %H:%M:%S') - 🚀 Spouštím vykupy actor (PID: $$)" >> "$LOG_FILE"

if [[ -f "$ACTOR_DIR/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ACTOR_DIR/.env"
  set +a
fi
export SYMPLIO_SCRIPTS_DIR="${SYMPLIO_SCRIPTS_DIR:-/opt/scripts/symplio-shared}"

cd "$ACTOR_DIR" || {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - ❌ Chyba: Adresář $ACTOR_DIR neexistuje" >> "$LOG_FILE"
    exit 1
}

export HEADLESS=1
HEADLESS=1 CHROME_BIN=/usr/bin/google-chrome /usr/bin/node main.js >> "$LOG_FILE" 2>&1

echo "$(date '+%Y-%m-%d %H:%M:%S') - ✅ Actor dokončen (PID: $$)" >> "$LOG_FILE"

exit 0
