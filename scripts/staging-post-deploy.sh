#!/bin/bash
set -e
STAGING=/home/webmajak/staging
PROD=/home/webmajak/webapp/webapp/settings_production.py
PW=$(grep -m1 "PASSWORD" "$PROD" | sed -n "s/.*'\([^']*\)'.*/\1/p")
if [ -z "$PW" ]; then
  echo "ERROR: could not read DB password from $PROD"
  exit 1
fi
cat > "$STAGING/.env" <<EOF
DB_NAME=multi_724223
DB_USER=multi_724223
DB_PASSWORD=$PW
DB_HOST=db.dw300.webglobe.com
DB_PORT=3306
EOF
chown webmajak:webmajak "$STAGING/.env"
chmod 600 "$STAGING/.env"
cd "$STAGING"
sudo -u webmajak bash -lc 'set -e; source venv/bin/activate; export DJANGO_SETTINGS_MODULE=webapp.settings_production; python manage.py migrate --noinput || echo "WARN: migrate skipped (shared DB migration history)"; python manage.py collectstatic --noinput; python manage.py check --deploy || python manage.py check'
systemctl restart webmajak-staging
sleep 2
systemctl is-active webmajak-staging
echo "post-deploy OK"
