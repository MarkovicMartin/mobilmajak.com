#!/bin/bash
# Návrh výjezdů na jinou prodejnu – cron na VPS. Idempotentní.
# Použití: ./scripts/install-vyjezd-navrh-cron.sh
#          STAGING=1 ./scripts/install-vyjezd-navrh-cron.sh
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

MARKER="# mobilmajak-vyjezd-navrh-${LABEL}"
TMP=/tmp/webmajak-crontab-vyjezd-${LABEL}.tmp

sudo -u webmajak crontab -l 2>/dev/null | grep -v "\$MARKER" | grep -v "cd \$APP_PATH && .*navrhni_vyjezdy" > "\$TMP" || true

cat >> "\$TMP" <<CRON

\$MARKER
20 6 * * 0 /bin/bash -lc 'd=\$(TZ=Europe/Prague date +%d); [ "\$d" -le 7 ] || exit 0; cd \$APP_PATH && source venv/bin/activate && export DJANGO_SETTINGS_MODULE=webapp.settings_production && python manage.py navrhni_vyjezdy >> logs/vyjezd-navrh.log 2>&1'
30 7 * * 0 /bin/bash -lc 'd=\$(TZ=Europe/Prague date +%d); [ "\$d" -le 7 ] || exit 0; cd \$APP_PATH && source venv/bin/activate && export DJANGO_SETTINGS_MODULE=webapp.settings_production && python manage.py navrhni_vyjezdy >> logs/vyjezd-navrh.log 2>&1'
CRON

sudo -u webmajak crontab "\$TMP"
rm -f "\$TMP"

echo "=== webmajak crontab (vyjezd navrh ${LABEL}) ==="
sudo -u webmajak crontab -l | grep -E 'navrhni_vyjezdy|mobilmajak-vyjezd-navrh' || true
EOF

echo "Cron návrhů výjezdů nastaven (${LABEL}, první neděle 6:20 a kontrola 7:30)."
