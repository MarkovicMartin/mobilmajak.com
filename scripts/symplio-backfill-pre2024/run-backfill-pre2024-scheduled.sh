#!/bin/bash
# Jednorázová večerní úloha: doplnění WEB_PRODEJE_ALL před 2024-01-01 (jen INSERT).
set -euo pipefail

ACTOR_DIR="/opt/actor/ACTOR_FINALL_WEB_PRODEJE_ALL"
cd "$ACTOR_DIR"

if [[ -f "$ACTOR_DIR/.env.db" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ACTOR_DIR/.env.db"
  set +a
fi

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

remove_cron() {
  (crontab -l 2>/dev/null | grep -v 'run-backfill-pre2024-scheduled' | grep -v "$CRON_TAG") | crontab - 2>/dev/null || true
}

if [[ -f "$LOCK" ]]; then
  OLD_PID=$(cat "$LOCK" 2>/dev/null || echo "")
  if [[ -n "$OLD_PID" ]] && kill -0 "$OLD_PID" 2>/dev/null; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Backfill už běží (PID $OLD_PID), končím." | tee -a "$LOG"
    exit 0
  fi
  rm -f "$LOCK"
fi

remove_cron

echo "" >> "$LOG"
log "========== NOVÝ BĚH =========="
log "=== Start backfill pre-2024 (insert-only, bez DELETE/ALTER) ==="

if ! bash "$ACTOR_DIR/test-backfill-pre2024-preflight.sh" >> "$LOG" 2>&1; then
  log "CHYBA: Preflight selhal – backfill se nespouští."
  exit 1
fi

echo $$ > "$LOCK"
trap 'rm -f "$LOCK"' EXIT

log "Stav před importem:"
if ! node -e "
const { connectToMySQL } = require('./main.js');
(async () => {
  const c = await connectToMySQL();
  const [r] = await c.execute('SELECT MIN(Vystaveno) mn, MAX(Vystaveno) mx, COUNT(*) n FROM WEB_PRODEJE_ALL');
  console.log('WEB_PRODEJE_ALL', r[0]);
  await c.end();
})().catch((e) => { console.error(e); process.exit(1); });
" >> "$LOG" 2>&1; then
  log "CHYBA: Nelze přečíst stav DB – backfill se nespouští."
  exit 1
fi

log "Spouštím backfill-pre2024-months.js (2017-10 .. 2023-12)..."
nohup node "$ACTOR_DIR/backfill-pre2024-months.js" >> "$LOG" 2>&1 &
BG_PID=$!
log "Backfill běží na pozadí PID=$BG_PID (log: $LOG)"
