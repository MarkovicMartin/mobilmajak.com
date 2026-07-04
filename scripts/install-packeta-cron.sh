#!/bin/bash
# Nainstaluje cron pro Packeta import na VPS (webmajak).
# Pobočky 1–6 jsou rozložené po 15 min (typický běh 3–6 min, timeout 10 min).
set -euo pipefail

SCRIPT_SRC="$(cd "$(dirname "$0")" && pwd)/run-packeta-import-safe.sh"
SCRIPT_DST="/opt/scripts/run-packeta-import-safe.sh"
CRON_FILE="/etc/cron.d/mobilmajak-packeta-import"

# Minuty mezi pobočkami v jedné vlně (15 = ~2× rezerva k 10min timeoutu)
STAGGER_MIN="${PACKETA_CRON_STAGGER_MIN:-15}"
AUDIT_STAGGER_MIN="${PACKETA_CRON_AUDIT_STAGGER_MIN:-20}"

echo "Kopíruji $SCRIPT_SRC -> $SCRIPT_DST"
sudo mkdir -p /opt/scripts
sudo cp "$SCRIPT_SRC" "$SCRIPT_DST"
sudo chmod +x "$SCRIPT_DST"

# generate_cron_line MODE BASE_HOUR BASE_MIN STAGGER PRODEJNA_ID [dow]
# offset = (id-1)*STAGGER minut od base; dow = * nebo 0 (neděle)
_cron_line() {
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
  printf '%d %d * * %s root %s%s %s %d\n' "$m" "$h" "$dow" "$env_prefix" "$SCRIPT_DST" "$mode" "$pid"
}

{
  echo "# Packeta import – 1 pobočka / běh, rozestup ${STAGGER_MIN} min, lock ve skriptu"
  echo "# Globus=1 Senimo=2 Zlín=3 Přerov=4 Vsetín=5 Šternberk=6"
  echo "#"
  echo "# Včera – vlna 5:00–6:15"
  for pid in 1 2 3 4 5 6; do
    _cron_line yesterday 5 0 "$STAGGER_MIN" "$pid"
  done
  echo "#"
  echo "# Dnes – vlny 10:00, 13:00, 16:30, 20:00 (každá ~75 min)"
  for slot in "10:0" "13:0" "16:30" "20:0"; do
    base_h=${slot%%:*}
    base_m=${slot##*:}
    for pid in 1 2 3 4 5 6; do
      _cron_line today "$base_h" "$base_m" "$STAGGER_MIN" "$pid"
    done
  done
  echo "#"
  echo "# Audit 7 dní – neděle 22:00–23:40, rozestup ${AUDIT_STAGGER_MIN} min"
  for pid in 1 2 3 4 5 6; do
    _cron_line audit 22 0 "$AUDIT_STAGGER_MIN" "$pid" 0
  done
} | sudo tee "$CRON_FILE" > /dev/null

sudo chmod 644 "$CRON_FILE"

echo "Cron ($CRON_FILE):"
echo "  Rozestup poboček: ${STAGGER_MIN} min (audit ${AUDIT_STAGGER_MIN} min)"
echo "  Timeout běhu: \${PACKETA_RUN_TIMEOUT:-600}s (10 min)"
echo "  Včera: 5:00–6:15 (6× yesterday)"
echo "  Dnes:  10:00–11:15, 13:00–14:15, 16:30–17:45, 20:00–21:15 (4×6× today)"
echo "  Audit: Ne 22:00–23:40 (6× audit 7 dní)"
echo "  Po každém běhu: backfill id_prodejce pro danou pobočku"
echo "Log: /var/log/packeta-import.log"
