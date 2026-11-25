#!/bin/bash
# Nainstaluje cron pro Packeta import a Symplio poznámky dokladů na VPS (webmajak).
# Rozvrh je sdílený – sloty uprav v packeta-cron-schedule.sh.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=packeta-cron-schedule.sh
source "$SCRIPT_DIR/packeta-cron-schedule.sh"

PACKETA_SCRIPT_SRC="$SCRIPT_DIR/run-packeta-import-safe.sh"
PACKETA_SCRIPT_DST="/opt/scripts/run-packeta-import-safe.sh"
PACKETA_CRON_FILE="/etc/cron.d/mobilmajak-packeta-import"

SYMPLIO_SCRIPT_SRC="$SCRIPT_DIR/run-symplio-doklad-notes-safe.sh"
SYMPLIO_SCRIPT_DST="/opt/scripts/run-symplio-doklad-notes-safe.sh"
SYMPLIO_CRON_FILE="/etc/cron.d/mobilmajak-symplio-doklad-notes"

echo "Kopíruji $PACKETA_SCRIPT_SRC -> $PACKETA_SCRIPT_DST"
sudo mkdir -p /opt/scripts
sudo cp "$PACKETA_SCRIPT_SRC" "$PACKETA_SCRIPT_DST"
sudo chmod +x "$PACKETA_SCRIPT_DST"

echo "Kopíruji $SYMPLIO_SCRIPT_SRC -> $SYMPLIO_SCRIPT_DST"
sudo cp "$SYMPLIO_SCRIPT_SRC" "$SYMPLIO_SCRIPT_DST"
sudo chmod +x "$SYMPLIO_SCRIPT_DST"

# generate_cron_line MODE BASE_HOUR BASE_MIN STAGGER PRODEJNA_ID [dow]
_packeta_cron_line() {
  local mode=$1 base_h=$2 base_m=$3 stagger=$4 pid=$5
  local dow="${6:-*}"
  local offset=$(( (pid - 1) * stagger ))
  local total=$(( base_h * 60 + base_m + offset ))
  local h=$(( total / 60 ))
  local m=$(( total % 60 ))
  local env_prefix=""
  if [ "$mode" = audit ]; then
    env_prefix="PACKETA_AUDIT_DAYS=7 "
  fi
  printf '%d %d * * %s root %s%s %s %d\n' "$m" "$h" "$dow" "$env_prefix" "$PACKETA_SCRIPT_DST" "$mode" "$pid"
}

# generate_symplio_cron_line MODE BASE_HOUR BASE_MIN [dow]
_symplio_cron_line() {
  local mode=$1 base_h=$2 base_m=$3
  local dow="${4:-*}"
  read -r cron_m cron_h <<< "$(cron_time_before_offset "$base_h" "$base_m" "$SYMPLIO_DOKLAD_NOTES_OFFSET_MIN")"
  printf '%d %d * * %s root %s %s\n' "$cron_m" "$cron_h" "$dow" "$SYMPLIO_SCRIPT_DST" "$mode"
}

{
  echo "# Packeta import – 1 pobočka / běh, rozestup ${PACKETA_CRON_STAGGER_MIN} min, lock ve skriptu"
  echo "# Globus=1 Senimo=2 Zlín=3 Přerov=4 Vsetín=5 Šternberk=6"
  echo "# Sloty: packeta-cron-schedule.sh"
  echo "#"
  echo "# Včera – jednou denně ${PACKETA_CRON_YESTERDAY_HOUR}:$(printf '%02d' "${PACKETA_CRON_YESTERDAY_MIN}")–…"
  for pid in 1 2 3 4 5 6; do
    _packeta_cron_line yesterday "$PACKETA_CRON_YESTERDAY_HOUR" "$PACKETA_CRON_YESTERDAY_MIN" "$PACKETA_CRON_STAGGER_MIN" "$pid"
  done
} | sudo tee "$PACKETA_CRON_FILE" > /dev/null

sudo chmod 644 "$PACKETA_CRON_FILE"

{
  echo "# Symplio poznámky dokladů – 1 běh / vlna, ${SYMPLIO_DOKLAD_NOTES_OFFSET_MIN} min před Packeta"
  echo "# Sloty: packeta-cron-schedule.sh (offset SYMPLIO_DOKLAD_NOTES_OFFSET_MIN)"
  echo "#"
  echo "# Včera, 15 min před Packetou"
  _symplio_cron_line yesterday "$PACKETA_CRON_YESTERDAY_HOUR" "$PACKETA_CRON_YESTERDAY_MIN"
} | sudo tee "$SYMPLIO_CRON_FILE" > /dev/null

sudo chmod 644 "$SYMPLIO_CRON_FILE"

echo ""
echo "Packeta cron ($PACKETA_CRON_FILE):"
echo "  Rozestup poboček: ${PACKETA_CRON_STAGGER_MIN} min"
echo "  Timeout běhu: \${PACKETA_RUN_TIMEOUT:-600}s (10 min)"
echo "  Jednou denně, včerejšek: ${PACKETA_CRON_YESTERDAY_HOUR}:$(printf '%02d' "${PACKETA_CRON_YESTERDAY_MIN}") + stagger"
echo "  Log: /var/log/packeta-import.log"
echo ""
echo "Symplio doklad notes cron ($SYMPLIO_CRON_FILE):"
echo "  Offset před Packeta: ${SYMPLIO_DOKLAD_NOTES_OFFSET_MIN} min"
echo "  Režim: yesterday, 15 min před Packetou"
echo "  Log: /var/log/symplio-doklad-notes.log"
echo ""
echo "Úprava rozvrhu: edituj scripts/packeta-cron-schedule.sh a znovu spusť tento skript."
