#!/bin/bash
# Cron pro plány na produkci (webmajak user). Idempotentní – nahradí staging variantu.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SSH_KEY="${SSH_KEY:-$REPO_ROOT/.ssh/webmajak_vps/mobilmajak_vps_ed25519}"
TARGET="${PRODUCTION_SSH:-root@194.182.87.138}"
WEBAPP_PATH="${WEBAPP_PATH:-/home/webmajak/webapp}"

if [ ! -f "$SSH_KEY" ]; then
  echo "SSH key not found: $SSH_KEY"
  exit 1
fi

ssh -i "$SSH_KEY" -o StrictHostKeyChecking=accept-new "$TARGET" bash -s <<EOF
set -euo pipefail
WEBAPP_PATH="$WEBAPP_PATH"
mkdir -p "\$WEBAPP_PATH/logs"
chown webmajak:webmajak "\$WEBAPP_PATH/logs"

MARKER="# mobilmajak-plans-cron"
TMP=/tmp/webmajak-crontab-plans.tmp

sudo -u webmajak crontab -l 2>/dev/null \
  | grep -v "\$MARKER" \
  | grep -v 'ensure_monthly_plans' \
  | grep -v 'prepocet_plan_prodejci' > "\$TMP" || true

cat >> "\$TMP" <<CRON

\$MARKER
0 6 1 * * /bin/bash -lc 'cd \$WEBAPP_PATH && source venv/bin/activate && export DJANGO_SETTINGS_MODULE=webapp.settings_production && python manage.py ensure_monthly_plans --rust 10 >> logs/ensure_monthly_plans.log 2>&1'
0 7 * * * /bin/bash -lc 'cd \$WEBAPP_PATH && source venv/bin/activate && export DJANGO_SETTINGS_MODULE=webapp.settings_production && python manage.py prepocet_plan_prodejci >> logs/prepocet_plan_prodejci.log 2>&1'
CRON

sudo -u webmajak crontab "\$TMP"
rm -f "\$TMP"

echo "=== webmajak crontab (plans → produkce) ==="
sudo -u webmajak crontab -l | grep -E 'ensure_monthly|prepocet_plan|mobilmajak-plans' || true
EOF

echo "Cron pro plány na produkci nastaven (\$WEBAPP_PATH/logs/)."
