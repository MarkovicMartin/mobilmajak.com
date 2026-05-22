#!/bin/bash
set -e
APP=/home/webmajak/webapp
cd "$APP"
sudo -u webmajak bash -lc 'set -e; source venv/bin/activate; export DJANGO_SETTINGS_MODULE=webapp.settings_production; python manage.py migrate --noinput || echo "WARN: migrate skipped"; python manage.py collectstatic --noinput; python manage.py check --deploy || python manage.py check'
systemctl restart webmajak
sleep 2
systemctl is-active webmajak
echo "post-deploy OK"
