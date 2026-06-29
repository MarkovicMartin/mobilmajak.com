#!/bin/bash
# Nainstaluje cron pro Packeta import 3× denně na VPS (webmajak).
set -euo pipefail

SCRIPT_SRC="$(cd "$(dirname "$0")" && pwd)/run-packeta-import-safe.sh"
SCRIPT_DST="/opt/scripts/run-packeta-import-safe.sh"
CRON_FILE="/etc/cron.d/mobilmajak-packeta-import"

echo "Kopíruji $SCRIPT_SRC -> $SCRIPT_DST"
sudo mkdir -p /opt/scripts
sudo cp "$SCRIPT_SRC" "$SCRIPT_DST"
sudo chmod +x "$SCRIPT_DST"

sudo tee "$CRON_FILE" > /dev/null <<EOF
# Packeta import – 3× denně (lock v run-packeta-import-safe.sh)
30 5 * * * root $SCRIPT_DST month
0 12 * * * root $SCRIPT_DST recent
0 18 * * * root $SCRIPT_DST recent
EOF

echo "Cron ($CRON_FILE):"
echo "  05:30 – celý měsíc (month)"
echo "  12:00 – poslední 3 dny (recent)"
echo "  18:00 – poslední 3 dny (recent)"
echo "Log: /var/log/packeta-import.log"
echo "Vyžaduje packeta_admin v secrets a playwright v venv."
