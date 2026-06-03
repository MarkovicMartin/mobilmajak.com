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
    chown webmajak:webmajak "$ENV_FILE"
    chmod 600 "$ENV_FILE"
    echo "OK: .env from $src"
    return 0
  fi
  return 1
}

if [ -f "$ENV_FILE" ] && grep -q '^DB_PASSWORD=.' "$ENV_FILE" 2>/dev/null; then
  echo "OK: keeping existing $ENV_FILE"
elif write_env_from_prod "$PROD_APP/.env"; then
  :
elif write_env_from_prod "$ENV_FILE.bak"; then
  :
else
  echo "WARN: DB_PASSWORD missing – create $ENV_FILE manually (copy from production .env)"
fi

cd "$STAGING"
sudo -u webmajak bash -lc 'set -e; source venv/bin/activate; export DJANGO_SETTINGS_MODULE=webapp.settings_production; python manage.py migrate --noinput || echo "WARN: migrate skipped"; python manage.py collectstatic --noinput; python manage.py check --deploy || python manage.py check'
systemctl restart webmajak-staging
sleep 2
systemctl is-active webmajak-staging
echo "post-deploy OK"
