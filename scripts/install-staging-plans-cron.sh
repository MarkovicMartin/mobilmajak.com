#!/bin/bash
# Přidá cron pro plány na staging VPS (webmajak user). Idempotentní.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SSH_KEY="${SSH_KEY:-$REPO_ROOT/.ssh/webmajak_vps/mobilmajak_vps_ed25519}"
TARGET="${STAGING_SSH:-root@194.182.87.138}"
STAGING_PATH="${STAGING_PATH:-/home/webmajak/staging}"

if [ ! -f "$SSH_KEY" ]; then
  echo "SSH key not found: $SSH_KEY"
  exit 1
fi

ssh -i "$SSH_KEY" -o StrictHostKeyChecking=accept-new "$TARGET" bash -s <<EOF
set -euo pipefail
STAGING_PATH="$STAGING_PATH"
mkdir -p "\$STAGING_PATH/logs"
chown webmajak:webmajak "\$STAGING_PATH/logs"

MARKER="# mobilmajak-plans-cron"
TMP=/tmp/webmajak-crontab.tmp

sudo -u webmajak crontab -l 2>/dev/null | grep -v "\$MARKER" | grep -v 'ensure_monthly_plans' | grep -v 'prepocet_plan_prodejci' > "\$TMP" || true

cat >> "\$TMP" <<CRON

\$MARKER
0 6 1 * * /bin/bash -lc 'cd \$STAGING_PATH && source venv/bin/activate && export DJANGO_SETTINGS_MODULE=webapp.settings_production && python manage.py ensure_monthly_plans --rust 10 >> logs/ensure_monthly_plans.log 2>&1'
0 7 * * * /bin/bash -lc 'cd \$STAGING_PATH && source venv/bin/activate && export DJANGO_SETTINGS_MODULE=webapp.settings_production && python manage.py prepocet_plan_prodejci >> logs/prepocet_plan_prodejci.log 2>&1'
CRON

sudo -u webmajak crontab "\$TMP"
rm -f "\$TMP"

echo "=== webmajak crontab (plans) ==="
sudo -u webmajak crontab -l | grep -E 'ensure_monthly|prepocet_plan|mobilmajak-plans' || true
EOF

echo "Cron pro plány na staging nastaven."
