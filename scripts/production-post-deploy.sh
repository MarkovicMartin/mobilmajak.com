#!/bin/bash
set -e
APP=/home/webmajak/webapp
ENV_FILE="$APP/.env"

# Zachovat / doplnit pilot kamer (stejně jako staging-post-deploy.sh)
if [ -f "$ENV_FILE" ]; then
  cp -a "$ENV_FILE" "$ENV_FILE.bak"
  if ! grep -q '^CAMERA_MOTION_SECRETS_FILE=' "$ENV_FILE" 2>/dev/null \
     && ! grep -q '^CAMERA_MOTION_SECRETS=' "$ENV_FILE" 2>/dev/null \
     && [ -f /home/webmajak/secrets/camera_motion_secrets.json ]; then
    echo 'CAMERA_MOTION_SECRETS_FILE=/home/webmajak/secrets/camera_motion_secrets.json' >> "$ENV_FILE"
    chown webmajak:webmajak "$ENV_FILE"
    chmod 600 "$ENV_FILE"
    echo "OK: doplněn CAMERA_MOTION_SECRETS_FILE do .env"
  fi
  if ! grep -q '^SHIFTS_CALENDAR_SEE_ALL_EMPLOYEES=' "$ENV_FILE" 2>/dev/null; then
    echo 'SHIFTS_CALENDAR_SEE_ALL_EMPLOYEES=1' >> "$ENV_FILE"
    chown webmajak:webmajak "$ENV_FILE"
    chmod 600 "$ENV_FILE"
    echo "OK: doplněn SHIFTS_CALENDAR_SEE_ALL_EMPLOYEES do .env"
  fi
  # Ostrý provoz orders Slack (ne test → Markovič)
  if grep -q '^ORDERS_SLACK_TEST_MODE=' "$ENV_FILE" 2>/dev/null; then
    sed -i 's/^ORDERS_SLACK_TEST_MODE=.*/ORDERS_SLACK_TEST_MODE=0/' "$ENV_FILE"
  else
    echo 'ORDERS_SLACK_TEST_MODE=0' >> "$ENV_FILE"
  fi
  chown webmajak:webmajak "$ENV_FILE"
  chmod 600 "$ENV_FILE"
  echo "OK: ORDERS_SLACK_TEST_MODE=0 (ostrý Slack provoz)"
fi

# Po přesunu Packeta do app packeta zůstávaly staré soubory ve finance/ a rozbíjely cron import.
rm -f "$APP/finance/packeta_fetch.py" "$APP/finance/packeta_parser.py" "$APP/finance/packeta_shift_assign.py" \
  "$APP/finance/management/commands/import_packeta_provize.py"

cd "$APP"
sudo -u webmajak bash -lc 'set -e; source venv/bin/activate; export DJANGO_SETTINGS_MODULE=webapp.settings_production; python manage.py migrate --noinput || echo "WARN: migrate skipped"; python manage.py normalize_packeta_zasilka || echo "WARN: normalize_packeta_zasilka skipped"; python manage.py collectstatic --noinput; python manage.py check --deploy || python manage.py check'
systemctl restart webmajak
sleep 2
systemctl is-active webmajak
echo "post-deploy OK"
