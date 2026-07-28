#!/bin/bash
# Post-deploy staging: .env, migrate, collectstatic, restart
set -e
STAGING=/home/webmajak/staging
PROD_APP=/home/webmajak/webapp
ENV_FILE="$STAGING/.env"

write_env_from_prod() {
  local src="$1"
  if [ -f "$src" ] && grep -q '^DB_PASSWORD=.' "$src" 2>/dev/null; then
    grep -E '^DB_(NAME|USER|PASSWORD|HOST|PORT)=' "$src" > "$ENV_FILE"
    # Preserve camera pilot config across deploys (post-deploy used to wipe these)
    if [ -f "$ENV_FILE.bak" ]; then
      grep -E '^CAMERA_MOTION_' "$ENV_FILE.bak" >> "$ENV_FILE" 2>/dev/null || true
    fi
    if ! grep -q '^CAMERA_MOTION_SECRETS_FILE=' "$ENV_FILE" 2>/dev/null \
       && ! grep -q '^CAMERA_MOTION_SECRETS=' "$ENV_FILE" 2>/dev/null \
       && [ -f /home/webmajak/secrets/camera_motion_secrets.json ]; then
      echo 'CAMERA_MOTION_SECRETS_FILE=/home/webmajak/secrets/camera_motion_secrets.json' >> "$ENV_FILE"
    fi
    chown webmajak:webmajak "$ENV_FILE"
    chmod 600 "$ENV_FILE"
    echo "OK: .env from $src"
    return 0
  fi
  return 1
}

if [ -f "$ENV_FILE" ] && grep -q '^DB_PASSWORD=.' "$ENV_FILE" 2>/dev/null; then
  cp -a "$ENV_FILE" "$ENV_FILE.bak"
  echo "OK: keeping existing $ENV_FILE (backed up to .env.bak)"
elif write_env_from_prod "$PROD_APP/.env"; then
  :
elif write_env_from_prod "$ENV_FILE.bak"; then
  :
else
  echo "WARN: DB_PASSWORD missing – create $ENV_FILE manually (copy from production .env)"
fi

# Stejná viditelnost směn jako na produkci (týmový kalendář pro všechny role)
if [ -f "$ENV_FILE" ]; then
  if ! grep -q '^SHIFTS_CALENDAR_SEE_ALL_EMPLOYEES=' "$ENV_FILE" 2>/dev/null; then
    echo 'SHIFTS_CALENDAR_SEE_ALL_EMPLOYEES=1' >> "$ENV_FILE"
    chown webmajak:webmajak "$ENV_FILE"
    chmod 600 "$ENV_FILE"
    echo "OK: doplněn SHIFTS_CALENDAR_SEE_ALL_EMPLOYEES do staging .env"
  fi
fi

rm -f "$STAGING/finance/packeta_fetch.py" "$STAGING/finance/packeta_parser.py" "$STAGING/finance/packeta_shift_assign.py" \
  "$STAGING/finance/management/commands/import_packeta_provize.py"

cd "$STAGING"
sudo -u webmajak bash -lc 'set -e; source venv/bin/activate; export DJANGO_SETTINGS_MODULE=webapp.settings_production; python manage.py migrate --noinput || echo "WARN: migrate skipped"; python manage.py normalize_packeta_zasilka || echo "WARN: normalize_packeta_zasilka skipped"; python manage.py collectstatic --noinput; python manage.py check --deploy || python manage.py check'
systemctl restart webmajak-staging
sleep 2
systemctl is-active webmajak-staging
# Staging není na bootu: po deployi běží jen do auto-stop (default 2h) / ručního stopu
if [ -x /opt/scripts/staging-app-control.sh ]; then
  STAGING_IDLE_TTL="${STAGING_IDLE_TTL:-2h}" /opt/scripts/staging-app-control.sh schedule-stop
else
  echo "WARN: chybí /opt/scripts/staging-app-control.sh – staging poběží bez auto-stop"
fi
echo "post-deploy OK (staging auto-stop TTL=${STAGING_IDLE_TTL:-2h})"
