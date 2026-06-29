#!/bin/bash
# Nainstaluje cron pro denní Packeta import na VPS (webmajak).
set -euo pipefail

SCRIPT_SRC="$(cd "$(dirname "$0")" && pwd)/run-packeta-import-safe.sh"
SCRIPT_DST="/opt/scripts/run-packeta-import-safe.sh"
CRON_LINE="30 5 * * * root $SCRIPT_DST"

echo "Kopíruji $SCRIPT_SRC -> $SCRIPT_DST"
sudo mkdir -p /opt/scripts
sudo cp "$SCRIPT_SRC" "$SCRIPT_DST"
sudo chmod +x "$SCRIPT_DST"

CRON_FILE="/etc/cron.d/mobilmajak-packeta-import"
if [ -f "$CRON_FILE" ] && grep -q "run-packeta-import-safe.sh" "$CRON_FILE"; then
  echo "Cron už existuje: $CRON_FILE"
else
  echo "$CRON_LINE" | sudo tee "$CRON_FILE" > /dev/null
  echo "Přidán cron: $CRON_LINE"
fi

echo "Log: /var/log/packeta-import.log"
echo "Vyžaduje packeta_admin v secrets a playwright v venv."
