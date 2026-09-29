#!/bin/bash
# Noční ověření odškrtnutých kategorií zboží. Idempotentní.
# Použití: ./scripts/install-kategorie-zbozi-cron.sh
#          STAGING=1 ./scripts/install-kategorie-zbozi-cron.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SSH_KEY="${SSH_KEY:-$REPO_ROOT/.ssh/webmajak_vps/mobilmajak_vps_ed25519}"
TARGET="${STAGING_SSH:-root@194.182.87.138}"

if [ "${STAGING:-0}" = "1" ]; then
  APP_PATH="${STAGING_PATH:-/home/webmajak/staging}"
  LABEL="staging"
else
  APP_PATH="${PRODUCTION_PATH:-/home/webmajak/webapp}"
  LABEL="production"
fi

if [ ! -f "$SSH_KEY" ]; then
  echo "SSH key not found: $SSH_KEY"
  exit 1
fi

ssh -i "$SSH_KEY" -o StrictHostKeyChecking=accept-new "$TARGET" bash -s <<EOF
set -euo pipefail
APP_PATH="$APP_PATH"
mkdir -p "\$APP_PATH/logs"
chown webmajak:webmajak "\$APP_PATH/logs"

MARKER="# mobilmajak-kategorie-zbozi-${LABEL}"
TMP=/tmp/webmajak-crontab-kategorie-zbozi-${LABEL}.tmp

sudo -u webmajak crontab -l 2>/dev/null | grep -v "\$MARKER" | grep -v 'kategorie_zbozi_kontrola' > "\$TMP" || true

cat >> "\$TMP" <<CRON

\$MARKER
30 23 * * * /bin/bash -lc 'cd \$APP_PATH && source venv/bin/activate && export DJANGO_SETTINGS_MODULE=webapp.settings_production && python manage.py kategorie_zbozi_kontrola >> logs/kategorie-zbozi.log 2>&1'
CRON

sudo -u webmajak crontab "\$TMP"
rm -f "\$TMP"

echo "=== webmajak crontab (kategorie zbozi ${LABEL}) ==="
sudo -u webmajak crontab -l | grep -E 'kategorie_zbozi_kontrola|mobilmajak-kategorie-zbozi' || true
EOF

echo "Cron kontroly kategorií nastaven (${LABEL}, 23:30)."
