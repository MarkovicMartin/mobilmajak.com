#!/bin/bash
# Nainstaluje cron pro finance importy na VPS.
# Symplio pokladna: dnešek každých 15 min 8:00–20:45 (strop 20 min),
#                   včerejšek + dnešek ráno v 6:40; Fio 3 dny denně ve 22:30.
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

# Denní běhy: jen dnešek. 8 pokladen se do 10 minut nevejde, strop je 20 min.
DAY_ENV="${CRON_ENV} SYMPLIO_POKLADNA_DAYS=1 SYMPLIO_POKLADNA_TIMEOUT=1200"
# Ráno po Packetě: včerejšek a dnešek. Dohání pohyb po posledním večerním běhu.
MORNING_ENV="${CRON_ENV} SYMPLIO_POKLADNA_DAYS=2 SYMPLIO_POKLADNA_TIMEOUT=1200"

echo "Kopíruji finance skripty do /opt/scripts"
sudo mkdir -p /opt/scripts
sudo cp "$ENV_SCRIPT_SRC" "$ENV_SCRIPT_DST"
sudo cp "$FIO_SCRIPT_SRC" "$FIO_SCRIPT_DST"
sudo chmod +x "$FIO_SCRIPT_DST"
sudo cp "$SYMPLIO_SCRIPT_SRC" "$SYMPLIO_SCRIPT_DST"
sudo chmod +x "$SYMPLIO_SCRIPT_DST"

{
  echo "# Finance modul – cron (Symplio pokladna + Fio)"
  echo "# Dnešek každých 15 min. Ráno v 6:40 včerejšek a dnešek. Fio denně 22:30."
  echo "#"
  echo "# Pohyby pokladen, jen dnešek, každých 15 min mezi 8:00 a 20:45"
  echo "*/15 8-20 * * * root ${DAY_ENV} $SYMPLIO_SCRIPT_DST"
  echo "#"
  echo "# Po Packetě: dohnání včerejšího pohybu, který přišel po 20:45"
  echo "40 6 * * * root ${MORNING_ENV} $SYMPLIO_SCRIPT_DST"
  echo "#"
  echo "# Fio a Raiffeisen každý den za 3 dny"
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
