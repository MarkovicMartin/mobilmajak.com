#!/bin/bash
# Nahraje skripty + .env.db na VPS a nastaví jednorázový cron na 20:30.
# Použití:
#   ./deploy-and-schedule.sh              # dnes 20:30
#   ./deploy-and-schedule.sh 2026-06-05   # konkrétní datum
#   ./deploy-and-schedule.sh today 21:00  # dnes 21:00
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
KEY="$REPO_ROOT/.ssh/webmajak_vps/mobilmajak_vps_ed25519"
HOST="root@194.182.87.138"
ACTOR="/opt/actor/ACTOR_FINALL_WEB_PRODEJE_ALL"
SRC="$REPO_ROOT/scripts/symplio-backfill-pre2024"
ENV_FILE="$REPO_ROOT/backend/.env"

CRON_HOUR="${CRON_HOUR:-20}"
CRON_MIN="${CRON_MIN:-30}"

if [[ "${1:-}" == "today" ]]; then
  SCHED_DATE="$(ssh -i "$KEY" "$HOST" "date +%Y-%m-%d")"
  [[ -n "${2:-}" ]] && CRON_HOUR="${2%%:*}" && CRON_MIN="${2##*:}"
elif [[ -n "${1:-}" ]]; then
  SCHED_DATE="$1"
else
  SCHED_DATE="$(ssh -i "$KEY" "$HOST" "date +%Y-%m-%d")"
fi

CRON_DAY="$(date -j -f "%Y-%m-%d" "$SCHED_DATE" "+%d" 2>/dev/null || date -d "$SCHED_DATE" "+%d")"
CRON_MONTH="$(date -j -f "%Y-%m-%d" "$SCHED_DATE" "+%m" 2>/dev/null || date -d "$SCHED_DATE" "+%m")"

if [[ ! -f "$KEY" ]]; then
  echo "Chybí SSH klíč: $KEY"
  exit 1
fi
if [[ ! -f "$ENV_FILE" ]]; then
  echo "Chybí $ENV_FILE (DB heslo)"
  exit 1
fi

echo "=== Deploy backfill pre-2024 ==="
echo "Termín: $SCHED_DATE ${CRON_HOUR}:${CRON_MIN} (server CEST)"

echo "[1] Nahrávám skripty..."
scp -i "$KEY" \
  "$SRC/backfill-pre2024-insert-only.js" \
  "$SRC/backfill-pre2024-months.js" \
  "$SRC/run-backfill-pre2024-scheduled.sh" \
  "$SRC/test-backfill-pre2024-preflight.sh" \
  "$SRC/compare.js" \
  "$HOST:${ACTOR}/"

echo "[2] Nahrávám .env.db (jen DB_* na VPS)..."
grep -E '^DB_(NAME|USER|PASSWORD|HOST|PORT)=' "$ENV_FILE" | ssh -i "$KEY" "$HOST" "cat > ${ACTOR}/.env.db && chmod 600 ${ACTOR}/.env.db"

ssh -i "$KEY" "$HOST" "chmod +x ${ACTOR}/run-backfill-pre2024-scheduled.sh ${ACTOR}/backfill-pre2024-insert-only.js ${ACTOR}/backfill-pre2024-months.js ${ACTOR}/test-backfill-pre2024-preflight.sh"

echo "[3] Preflight na VPS..."
ssh -i "$KEY" "$HOST" "bash ${ACTOR}/test-backfill-pre2024-preflight.sh"

CRON_LINE="${CRON_MIN} ${CRON_HOUR} ${CRON_DAY} ${CRON_MONTH} * ${ACTOR}/run-backfill-pre2024-scheduled.sh >> ${ACTOR}/reports/backfill_pre2024_cron.log 2>&1 # mobilmajak-pre2024-once"

echo "[4] Nastavuji cron..."
ssh -i "$KEY" "$HOST" bash -s <<EOF
set -euo pipefail
( crontab -l 2>/dev/null | grep -v 'run-backfill-pre2024-scheduled' | grep -v 'mobilmajak-pre2024-once' || true
  echo "$CRON_LINE"
) | crontab -
echo "Cron:"
crontab -l | grep mobilmajak-pre2024-once
EOF

echo ""
echo "Hotovo. Backfill: $SCHED_DATE ${CRON_HOUR}:${CRON_MIN}"
echo "Log: ${ACTOR}/reports/backfill_pre2024_scheduled.log"
