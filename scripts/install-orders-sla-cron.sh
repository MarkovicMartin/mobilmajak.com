#!/bin/bash
# Připomínky objednávek (stale Po–Pá + 7d eskalace) – cron na VPS. Idempotentní.
# Použití: ./scripts/install-orders-sla-cron.sh          # produkce
#          STAGING=1 ./scripts/install-orders-sla-cron.sh  # staging
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

MARKER="# mobilmajak-orders-slack-${LABEL}"
TMP=/tmp/webmajak-crontab-orders-slack-${LABEL}.tmp

sudo -u webmajak crontab -l 2>/dev/null | grep -v "\$MARKER" | grep -v 'check_orders_sla_reminders' | grep -v 'check_orders_stale_reminders' > "\$TMP" || true

cat >> "\$TMP" <<CRON

\$MARKER
0 8 * * 1-5 /bin/bash -lc 'cd \$APP_PATH && source venv/bin/activate && export DJANGO_SETTINGS_MODULE=webapp.settings_production && python manage.py check_orders_stale_reminders >> logs/orders-stale-reminders.log 2>&1'
20 7 * * * /bin/bash -lc 'cd \$APP_PATH && source venv/bin/activate && export DJANGO_SETTINGS_MODULE=webapp.settings_production && python manage.py check_orders_sla_reminders >> logs/orders-sla-reminders.log 2>&1'
CRON

sudo -u webmajak crontab "\$TMP"
rm -f "\$TMP"

echo "=== webmajak crontab (orders Slack ${LABEL}) ==="
sudo -u webmajak crontab -l | grep -E 'check_orders_(sla|stale)_reminders|mobilmajak-orders-slack' || true
EOF

echo "Cron pro objednávkové Slack připomínky nastaven (${LABEL}: stale Po–Pá 8:00, 7d eskalace denně 7:20)."
