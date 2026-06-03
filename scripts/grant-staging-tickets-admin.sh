#!/bin/bash
# Udělí uživateli modul tickets_admin na staging (správa ticketů).
# Usage: ./scripts/grant-staging-tickets-admin.sh markovic

set -euo pipefail

USER_NAME="${1:-}"
if [ -z "$USER_NAME" ]; then
  echo "Usage: $0 <uzivatelske_jmeno>"
  echo "Example: $0 markovic"
  exit 1
fi

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SSH_KEY="${SSH_KEY:-$REPO_ROOT/.ssh/webmajak_vps/mobilmajak_vps_ed25519}"
TARGET="root@194.182.87.138"
STAGING="/home/webmajak/staging"

if [ ! -f "$SSH_KEY" ]; then
  echo "SSH key not found: $SSH_KEY"
  exit 1
fi

ssh -i "$SSH_KEY" -o StrictHostKeyChecking=accept-new "$TARGET" \
  "sudo -u webmajak bash -lc 'cd ${STAGING} && source venv/bin/activate && export DJANGO_SETTINGS_MODULE=webapp.settings_production && python manage.py grant_tickets_admin ${USER_NAME}'"

echo ""
echo "Hotovo. Uživatel se musí odhlásit a znovu přihlásit, aby načetl moduly."
