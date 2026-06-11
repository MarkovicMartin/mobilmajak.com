#!/bin/bash
# Smoke test po deployi. Usage: ./scripts/post-deploy-smoke.sh staging|production
set -euo pipefail

ENV="${1:-}"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SSH_KEY="${SSH_KEY:-$REPO_ROOT/.ssh/webmajak_vps/mobilmajak_vps_ed25519}"
TARGET="root@194.182.87.138"
SSH_OPTS=(-i "$SSH_KEY" -o StrictHostKeyChecking=accept-new)

case "$ENV" in
  staging)
    BASE_URL="https://staging.mobilmajak.com"
    APP_PATH="/home/webmajak/staging"
    ;;
  production)
    BASE_URL="https://mobilmajak.com"
    APP_PATH="/home/webmajak/webapp"
    ;;
  *)
    echo "Usage: $0 staging|production"
    exit 1
    ;;
esac

echo "=== Smoke: $ENV ==="

HEALTH=$(curl -sf -o /dev/null -w "%{http_code}" "$BASE_URL/health/" 2>/dev/null || echo "000")
if [ "$HEALTH" != "200" ]; then
  echo "FAIL health HTTP $HEALTH"
  exit 1
fi
echo "OK health"

ssh "${SSH_OPTS[@]}" "$TARGET" "sudo -u webmajak bash -lc '
  set -e
  cd $APP_PATH
  source venv/bin/activate
  export DJANGO_SETTINGS_MODULE=webapp.settings_production
  python manage.py check
  python -c \"
import django
django.setup()
from shifts.czech_holidays import get_ceske_svatky, get_nazev_svatku
import shifts.views  # noqa: F401 – chytí chybějící importy ve views
assert get_ceske_svatky(2026)
print(\\\"OK shifts\\\")
\"
'"
echo "=== Smoke passed ==="
