#!/bin/bash
# Nahraje skripty na VPS a nastaví jednorázový cron na 20:30 (4. 6.).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
KEY="$REPO_ROOT/.ssh/webmajak_vps/mobilmajak_vps_ed25519"
HOST="root@194.182.87.138"
ACTOR="/opt/actor/ACTOR_FINALL_WEB_PRODEJE_ALL"
SRC="$REPO_ROOT/scripts/symplio-backfill-pre2024"

if [ ! -f "$KEY" ]; then
  echo "Chybí SSH klíč: $KEY"
  exit 1
fi

echo "Nahrávám skripty na VPS..."
scp -i "$KEY" \
  "$SRC/backfill-pre2024-insert-only.js" \
  "$SRC/backfill-pre2024-months.js" \
  "$SRC/run-backfill-pre2024-scheduled.sh" \
  "$HOST:${ACTOR}/"

ssh -i "$KEY" "$HOST" "chmod +x ${ACTOR}/run-backfill-pre2024-scheduled.sh ${ACTOR}/backfill-pre2024-insert-only.js ${ACTOR}/backfill-pre2024-months.js"

CRON_LINE="30 20 4 6 * ${ACTOR}/run-backfill-pre2024-scheduled.sh >> ${ACTOR}/reports/backfill_pre2024_cron.log 2>&1 # mobilmajak-pre2024-once"

echo "Nastavuji cron (20:30 dnes, jednorázově)..."
ssh -i "$KEY" "$HOST" bash -s <<EOF
set -euo pipefail
( crontab -l 2>/dev/null | grep -v 'run-backfill-pre2024-scheduled' | grep -v 'mobilmajak-pre2024-once' || true
  echo "$CRON_LINE"
) | crontab -
echo "Aktuální cron (backfill):"
crontab -l | grep -E 'backfill-pre2024|mobilmajak-pre2024' || echo '(řádek nenalezen – zkontroluj crontab -l)'
EOF

echo ""
echo "Hotovo. Dnes v 20:30 VPS spustí run-backfill-pre2024-scheduled.sh"
echo "Log: ${ACTOR}/reports/backfill_pre2024_scheduled.log"
echo "Sledování: ssh -i $KEY $HOST tail -f ${ACTOR}/reports/backfill_pre2024_scheduled.log"
