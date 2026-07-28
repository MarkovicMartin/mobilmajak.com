#!/bin/bash
# Slack notifikace úkolů – cron na VPS. Idempotentní.
#   - notify_shift_task_recap  … ranní shrnutí 10 min po začátku směny (*/5)
#   - notify_task_deadlines    … due_soon / overdue DM (každou hodinu)
# Použití: ./scripts/install-task-slack-notify-cron.sh          # produkce
#          STAGING=1 ./scripts/install-task-slack-notify-cron.sh  # staging
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

MARKER="# mobilmajak-task-slack-notify-${LABEL}"
TMP=/tmp/webmajak-crontab-task-slack-${LABEL}.tmp

sudo -u webmajak crontab -l 2>/dev/null \
  | grep -v "\$MARKER" \
  | grep -v 'notify_shift_task_recap' \
  | grep -v 'notify_task_deadlines' \
  > "\$TMP" || true

cat >> "\$TMP" <<CRON

\$MARKER
*/5 * * * * /bin/bash -lc 'cd \$APP_PATH && source venv/bin/activate && export DJANGO_SETTINGS_MODULE=webapp.settings_production && python manage.py notify_shift_task_recap >> logs/task-shift-recap.log 2>&1'
0 * * * * /bin/bash -lc 'cd \$APP_PATH && source venv/bin/activate && export DJANGO_SETTINGS_MODULE=webapp.settings_production && python manage.py notify_task_deadlines >> logs/task-slack-notify.log 2>&1'
CRON

sudo -u webmajak crontab "\$TMP"
rm -f "\$TMP"

echo "=== webmajak crontab (task slack notify ${LABEL}) ==="
sudo -u webmajak crontab -l | grep -E 'notify_shift_task_recap|notify_task_deadlines|mobilmajak-task-slack' || true
EOF

echo "Cron pro Slack notifikace úkolů nastaven (${LABEL}):"
echo "  - shift recap: každých 5 min"
echo "  - deadlines: každou hodinu"
