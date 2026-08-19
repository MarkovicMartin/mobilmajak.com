#!/bin/bash
# Denní Slack report – cron na produkčním VPS (webmajak user). Idempotentní.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SSH_KEY="${SSH_KEY:-$REPO_ROOT/.ssh/webmajak_vps/mobilmajak_vps_ed25519}"
TARGET="${PRODUCTION_SSH:-root@194.182.87.138}"
PROD_PATH="${PRODUCTION_PATH:-/home/webmajak/webapp}"

if [ ! -f "$SSH_KEY" ]; then
  echo "SSH key not found: $SSH_KEY"
  exit 1
fi

ssh -i "$SSH_KEY" -o StrictHostKeyChecking=accept-new "$TARGET" bash -s <<EOF
set -euo pipefail
PROD_PATH="$PROD_PATH"
mkdir -p "\$PROD_PATH/logs"
chown webmajak:webmajak "\$PROD_PATH/logs"

MARKER="# mobilmajak-daily-slack-report"
TMP=/tmp/webmajak-crontab-daily-report.tmp

sudo -u webmajak crontab -l 2>/dev/null | grep -v "\$MARKER" | grep -v 'send_daily_slack_report' > "\$TMP" || true

cat >> "\$TMP" <<CRON

\$MARKER
35 20 * * * /bin/bash -lc 'cd \$PROD_PATH && source venv/bin/activate && export DJANGO_SETTINGS_MODULE=webapp.settings_production && python manage.py send_daily_slack_report >> logs/daily-slack-report.log 2>&1'
CRON

sudo -u webmajak crontab "\$TMP"
rm -f "\$TMP"

echo "=== webmajak crontab (daily slack report) ==="
sudo -u webmajak crontab -l | grep -E 'send_daily_slack_report|mobilmajak-daily-slack' || true
EOF

echo "Cron pro denní Slack report nastaven (20:35 každý den)."
