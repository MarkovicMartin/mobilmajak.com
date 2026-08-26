#!/bin/bash
# Nainstaluje cron pro finance importy na VPS.
# Symplio pokladna: denní výdeje 8:30–21:00 (mimo Packeta/Symplio notes),
#                   večerní full catch-up 22:00; Fio 22:30.
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

# Denní běhy: jen dnešek, kratší timeout (méně zátěže vedle Packety).
DAY_ENV="${CRON_ENV} SYMPLIO_POKLADNA_DAYS=1 SYMPLIO_POKLADNA_TIMEOUT=600"

echo "Kopíruji finance skripty do /opt/scripts"
sudo mkdir -p /opt/scripts
sudo cp "$ENV_SCRIPT_SRC" "$ENV_SCRIPT_DST"
sudo cp "$FIO_SCRIPT_SRC" "$FIO_SCRIPT_DST"
sudo chmod +x "$FIO_SCRIPT_DST"
sudo cp "$SYMPLIO_SCRIPT_SRC" "$SYMPLIO_SCRIPT_DST"
sudo chmod +x "$SYMPLIO_SCRIPT_DST"

{
  echo "# Finance modul – cron (Symplio pokladna + Fio)"
  echo "# Slotyminuty :10/:40 (a 8:30, 21:00) – mimo Packeta :00/:15/:30/:45"
  echo "# a mimo Symplio doklad-notes (:15/:45 před Packeta vlnami)."
  echo "#"
  echo "# Denní výdeje → finance (jen dnešek), 8:30–21:00"
  echo "30 8 * * * root ${DAY_ENV} $SYMPLIO_SCRIPT_DST"
  echo "10,40 9-20 * * * root ${DAY_ENV} $SYMPLIO_SCRIPT_DST"
  echo "0 21 * * * root ${DAY_ENV} $SYMPLIO_SCRIPT_DST"
  echo "#"
  echo "# Večerní full catch-up (7 dní default) + Fio"
  echo "0 22 * * * root ${CRON_ENV} $SYMPLIO_SCRIPT_DST"
  echo "30 22 * * * root ${CRON_ENV} FINANCE_IMPORT_DAYS=3 $FIO_SCRIPT_DST"
} | sudo tee "$CRON_FILE" > /dev/null
sudo chmod 644 "$CRON_FILE"

echo "Cron nainstalován: $CRON_FILE"
echo ""
cat "$CRON_FILE"
echo ""
echo "Vyžaduje v backend/.env na VPS:"
echo "  FINANCE_MODULE_ENABLED=1"
echo "  FINANCE_FIO_ENABLED=1  (až po admin účtu)"
echo "  FINANCE_SECRETS_FILE=..."
