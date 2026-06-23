#!/bin/bash
# Backfill skladových výdejek po měsících na VPS.
# Usage: ./scripts/backfill-sklad-vydejky.sh 2026-01 2026-06
set -euo pipefail

if [ $# -lt 2 ]; then
  echo "Usage: $0 YYYY-MM YYYY-MM"
  exit 1
fi

START_YM="$1"
END_YM="$2"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SSH_KEY="${SSH_KEY:-$REPO_ROOT/.ssh/webmajak_vps/mobilmajak_vps_ed25519}"
TARGET="root@194.182.87.138"
ACTOR_DIR="/opt/actor/ACTOR_FINALL_WEB_PRODEJE_ALL"

ym_to_first() { date -j -f "%Y-%m-%d" "${1}-01" "+%Y-%m-%d" 2>/dev/null || date -d "${1}-01" "+%Y-%m-%d"; }
ym_to_last() {
  local y m
  y=$(echo "$1" | cut -d- -f1)
  m=$(echo "$1" | cut -d- -f2)
  date -j -f "%Y-%m-%d" "${y}-${m}-01" "+%Y-%m-%d" 2>/dev/null && \
    date -j -v1d -v+1m -v-1d -f "%Y-%m-%d" "${y}-${m}-01" "+%Y-%m-%d" 2>/dev/null || \
    date -d "${y}-${m}-01 +1 month -1 day" "+%Y-%m-%d"
}

echo "Deploy import script..."
scp -i "$SSH_KEY" "$REPO_ROOT/actors_backup/import-sklad-vydejky.js" "${TARGET}:${ACTOR_DIR}/import-sklad-vydejky.js"

CUR="$START_YM"
while [ "$(printf '%s\n' "$CUR" "$END_YM" | sort | head -1)" = "$CUR" ]; do
  FROM=$(ym_to_first "$CUR")
  TO=$(ym_to_last "$CUR")
  echo "=== Backfill $CUR ($FROM .. $TO) ==="
  ssh -i "$SSH_KEY" "$TARGET" "cd $ACTOR_DIR && HEADLESS=1 CHROME_BIN=/usr/bin/google-chrome node import-sklad-vydejky.js --from $FROM --to $TO"
  # next month
  CUR=$(date -j -f "%Y-%m-%d" "${CUR}-01" "+%Y-%m" 2>/dev/null && date -j -v+1m -f "%Y-%m-%d" "${CUR}-01" "+%Y-%m" 2>/dev/null || date -d "${CUR}-01 +1 month" "+%Y-%m")
done

echo "Backfill hotovo."
