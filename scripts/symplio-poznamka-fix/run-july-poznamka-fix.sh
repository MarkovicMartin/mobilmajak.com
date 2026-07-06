#!/usr/bin/env bash
# Backfill položek + doplnění Poznamka_dokladu přes sync-doklad-notes (ne z exportu položek).
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
KEY="${MOBILMAJAK_SSH_KEY:-$REPO_ROOT/.ssh/webmajak_vps/mobilmajak_vps_ed25519}"
ACTOR="/opt/actor/ACTOR_FINALL_WEB_PRODEJE_ALL"
FROM="${1:-2026-07-01}"
TO="${2:-2026-07-04}"
DB_PASS=$(grep '^DB_PASSWORD=' "$REPO_ROOT/backend/.env" | cut -d= -f2)
DB_HOST=$(grep '^DB_HOST=' "$REPO_ROOT/backend/.env" | cut -d= -f2)
DB_USER=$(grep '^DB_USER=' "$REPO_ROOT/backend/.env" | cut -d= -f2)
DB_NAME=$(grep '^DB_NAME=' "$REPO_ROOT/backend/.env" | cut -d= -f2)

echo "==> Nahrávám skripty na VPS"
scp -i "$KEY" \
  "$REPO_ROOT/scripts/symplio-poznamka-fix/main.js" \
  "$REPO_ROOT/scripts/symplio-poznamka-fix/symplio-credentials.js" \
  "$REPO_ROOT/scripts/symplio-poznamka-fix/symplio-login.js" \
  "$REPO_ROOT/scripts/symplio-poznamka-fix/sync-doklad-notes.js" \
  "$REPO_ROOT/scripts/symplio-poznamka-fix/fetch-doklad-notes.js" \
  "$REPO_ROOT/scripts/symplio-poznamka-fix/apply-poznamka-dokladu.js" \
  "$REPO_ROOT/scripts/symplio-poznamka-fix/snapshot-july.js" \
  "$REPO_ROOT/scripts/symplio-poznamka-fix/compare-notes.js" \
  "$REPO_ROOT/scripts/symplio-poznamka-fix/restore-from-snapshot.js" \
  "root@194.182.87.138:${ACTOR}/"

SYMPLIO_ENV="set -a && source ${ACTOR}/.env && set +a"

echo "==> Snapshot BEFORE (pokud neexistuje)"
ssh -i "$KEY" root@194.182.87.138 "cd ${ACTOR} && export DB_HOST='$DB_HOST' DB_USER='$DB_USER' DB_NAME='$DB_NAME' DB_PASSWORD='$DB_PASS' && \
  test -f reports/snapshot_2026-07_before.json || node snapshot-july.js --year 2026 --month 7 --out reports/snapshot_2026-07_before.json"

echo "==> Backfill položek ${FROM}..${TO} (Poznamka_dokladu jen přes sync-doklad-notes)"
ssh -i "$KEY" root@194.182.87.138 "cd ${ACTOR} && export DB_HOST='$DB_HOST' DB_USER='$DB_USER' DB_NAME='$DB_NAME' DB_PASSWORD='$DB_PASS' && \
  node backfill-historical.js --from ${FROM} --to ${TO} --file reports/symplio_${FROM}_${TO}.xlsx 2>&1 | tee reports/backfill_poznamka_${FROM}_${TO}.log || \
  node backfill-historical.js --from ${FROM} --to ${TO} --download 2>&1 | tee reports/backfill_poznamka_${FROM}_${TO}.log"

echo "==> Poznámky dokladů ze seznamu dokladů Symplio (fetch + apply)"
ssh -i "$KEY" root@194.182.87.138 "cd ${ACTOR} && ${SYMPLIO_ENV} && HEADLESS=1 CHROME_BIN=/usr/bin/google-chrome node fetch-doklad-notes.js --from ${FROM} --to ${TO} --out reports/poznamka_dokladu_enrichment.json && \
  node apply-poznamka-dokladu.js --json reports/poznamka_dokladu_enrichment.json --from ${FROM} --to ${TO}"

echo "==> Compare notes"
ssh -i "$KEY" root@194.182.87.138 "cd ${ACTOR} && export DB_HOST='$DB_HOST' DB_USER='$DB_USER' DB_NAME='$DB_NAME' DB_PASSWORD='$DB_PASS' && \
  node compare-notes.js --before reports/snapshot_2026-07_before.json"

echo "==> Hotovo. Rollback: node restore-from-snapshot.js --file reports/snapshot_2026-07_before.json"
