#!/bin/bash
# Jednorázový backfill Fio + Symplio pokladna za květen a červen 2026.
# Spustit na VPS jako root (cron wrapper používá sudo -u webmajak u manage.py).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=finance-webapp-env.sh
source "$SCRIPT_DIR/finance-webapp-env.sh"
finance_resolve_webapp "$SCRIPT_DIR"

ACTOR_DIR="${SYMPLIO_POKLADNA_DIR:-$SCRIPT_DIR/symplio-pokladna-historie}"
REPORTS_DIR="$ACTOR_DIR/reports"
LOG="${BACKFILL_LOG:-$SCRIPT_DIR/../logs/finance-backfill-may-june.log}"
FIO_SLEEP="${FIO_API_SLEEP:-35}"

log() { echo "$(date '+%Y-%m-%d %H:%M:%S') $*" | tee -a "$LOG"; }

import_fio_range() {
  local from="$1" to="$2"
  log "Fio import $from – $to"
  local cmd
  cmd=$(finance_manage_cmd "import_fio_naklady --date-from $from --date-to $to --skip-balance")
  eval "$cmd" >> "$LOG" 2>&1
  log "Fio hotovo $from – $to, čekám ${FIO_SLEEP}s (rate limit)"
  sleep "$FIO_SLEEP"
}

import_symplio_range() {
  local from="$1" to="$2"
  log "Symplio pokladna $from – $to"
  (
    cd "$ACTOR_DIR"
    if [[ -f .env ]]; then set -a; source .env; set +a; fi
    export SYMPLIO_DATE_FROM="$from" SYMPLIO_DATE_TO="$to"
    export SYMPLIO_POKLADNA_TIMEOUT="${SYMPLIO_POKLADNA_TIMEOUT:-1800}"
    node fetch-pokladna-xlsx.js
  ) >> "$LOG" 2>&1
  local cmd
  cmd=$(finance_manage_cmd "import_symplio_pokladna --input-dir '$REPORTS_DIR'")
  eval "$cmd" >> "$LOG" 2>&1
  log "Symplio hotovo $from – $to"
}

log "=== Backfill finance květen + červen 2026 ==="

import_fio_range 2026-05-01 2026-05-31
import_fio_range 2026-06-01 2026-06-30

import_symplio_range 2026-05-01 2026-05-31
import_symplio_range 2026-06-01 2026-06-30

log "=== Backfill dokončen ==="
