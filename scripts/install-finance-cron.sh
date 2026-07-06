#!/bin/bash
# Nainstaluje cron pro finance importy na VPS.
# Rozvrh: Symplio pokladna 22:00, Fio náklady 22:30 (mimo Packeta špičku).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

FIO_SCRIPT_SRC="$SCRIPT_DIR/run-finance-import-safe.sh"
FIO_SCRIPT_DST="/opt/scripts/run-finance-import-safe.sh"
SYMPLIO_SCRIPT_SRC="$SCRIPT_DIR/run-symplio-pokladna-safe.sh"
SYMPLIO_SCRIPT_DST="/opt/scripts/run-symplio-pokladna-safe.sh"
ENV_SCRIPT_SRC="$SCRIPT_DIR/finance-webapp-env.sh"
ENV_SCRIPT_DST="/opt/scripts/finance-webapp-env.sh"
CRON_FILE="/etc/cron.d/mobilmajak-finance"
WEBAPP_PATH="${WEBAPP_PATH:-/home/webmajak/webapp}"
CRON_ENV="WEBAPP_PATH=${WEBAPP_PATH}"

echo "Kopíruji finance skripty do /opt/scripts"
sudo mkdir -p /opt/scripts
sudo cp "$ENV_SCRIPT_SRC" "$ENV_SCRIPT_DST"
sudo cp "$FIO_SCRIPT_SRC" "$FIO_SCRIPT_DST"
sudo chmod +x "$FIO_SCRIPT_DST"
sudo cp "$SYMPLIO_SCRIPT_SRC" "$SYMPLIO_SCRIPT_DST"
sudo chmod +x "$SYMPLIO_SCRIPT_DST"

{
  echo "# Finance modul – cron rozvrh (večer, mimo Packeta)"
  echo "# Symplio historie pokladny (výdeje → finance)"
  echo "0 22 * * * root ${CRON_ENV} $SYMPLIO_SCRIPT_DST"
  echo "# Fio import nákladů + balance snapshot"
  echo "30 22 * * * root ${CRON_ENV} FINANCE_IMPORT_DAYS=3 $FIO_SCRIPT_DST"
} | sudo tee "$CRON_FILE" > /dev/null

echo "Cron nainstalován: $CRON_FILE"
echo ""
echo "Vyžaduje v backend/.env na VPS:"
echo "  FINANCE_MODULE_ENABLED=1"
echo "  FINANCE_FIO_ENABLED=1  (až po admin účtu)"
echo "  FINANCE_SECRETS_FILE=..."
