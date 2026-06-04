#!/bin/bash
# Jednorázová večerní úloha: doplnění WEB_PRODEJE_ALL před 2024-01-01 (jen INSERT).
set -euo pipefail

ACTOR_DIR="/opt/actor/ACTOR_FINALL_WEB_PRODEJE_ALL"
cd "$ACTOR_DIR"

export DB_HOST="${DB_HOST:-db.dw300.webglobe.com}"
export DB_USER="${DB_USER:-multi_724223}"
export DB_NAME="${DB_NAME:-multi_724223}"
export BACKFILL_CUTOFF_DATE="2024-01-01"

REPORTS="$ACTOR_DIR/reports"
mkdir -p "$REPORTS"
LOG="$REPORTS/backfill_pre2024_scheduled.log"
LOCK="$REPORTS/backfill_pre2024.lock"
CRON_TAG="mobilmajak-pre2024-once"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG"
}

# Odstranit jednorázový cron hned po startu (neběží znovu zítra)
remove_cron() {
  (crontab -l 2>/dev/null | grep -v 'run-backfill-pre2024-scheduled' | grep -v "$CRON_TAG") | crontab - 2>/dev/null || true
}

if [ -f "$LOCK" ]; then
  OLD_PID=$(cat "$LOCK" 2>/dev/null || echo "")
  if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
    log "Backfill už běží (PID $OLD_PID), končím."
    exit 0
  fi
  rm -f "$LOCK"
fi

echo $$ > "$LOCK"
trap 'rm -f "$LOCK"' EXIT

remove_cron
log "=== Start backfill pre-2024 (insert-only, bez DELETE/ALTER) ==="

log "Stav před importem:"
node -e "
const m=require('mysql2/promise');
(async()=>{
  const c=await m.createConnection({
    host:process.env.DB_HOST,user:process.env.DB_USER,
    password:process.env.DB_PASSWORD||process.env.MYSQL_PASSWORD,
    database:process.env.DB_NAME
  });
  const [r]=await c.execute('SELECT MIN(Vystaveno) mn, MAX(Vystaveno) mx, COUNT(*) n FROM WEB_PRODEJE_ALL');
  console.log('WEB_PRODEJE_ALL', r[0]);
  await c.end();
})().catch(e=>{console.error(e);process.exit(1)});
" 2>&1 | tee -a "$LOG"

log "Spouštím backfill-pre2024-months.js (2017-10 .. 2023-12)..."
nohup node "$ACTOR_DIR/backfill-pre2024-months.js" >> "$LOG" 2>&1 &
BG_PID=$!
log "Backfill běží na pozadí PID=$BG_PID (log: $LOG)"
