#!/bin/bash
# Nainstaluje cron pro Packeta import na VPS (webmajak).
set -euo pipefail

SCRIPT_SRC="$(cd "$(dirname "$0")" && pwd)/run-packeta-import-safe.sh"
SCRIPT_DST="/opt/scripts/run-packeta-import-safe.sh"
CRON_FILE="/etc/cron.d/mobilmajak-packeta-import"

echo "Kopíruji $SCRIPT_SRC -> $SCRIPT_DST"
sudo mkdir -p /opt/scripts
sudo cp "$SCRIPT_SRC" "$SCRIPT_DST"
sudo chmod +x "$SCRIPT_DST"

sudo tee "$CRON_FILE" > /dev/null <<EOF
# Packeta import – lock v run-packeta-import-safe.sh, get_or_create (bez přepisu)
30 5 * * * root $SCRIPT_DST yesterday
0 10 * * * root $SCRIPT_DST today
0 13 * * * root $SCRIPT_DST today
30 16 * * * root $SCRIPT_DST today
0 20 * * * root $SCRIPT_DST today
0 23 * * 0 root $SCRIPT_DST audit
EOF

echo "Cron ($CRON_FILE):"
echo "  05:30 – včera (uzavření dne)"
echo "  10:00 – dnes (průběh)"
echo "  13:00 – dnes"
echo "  16:30 – dnes"
echo "  20:00 – dnes"
echo "  Ne 23:00 – audit 7 dní"
echo "Log: /var/log/packeta-import.log"
echo "Vyžaduje packeta_admin v secrets a playwright v venv."
