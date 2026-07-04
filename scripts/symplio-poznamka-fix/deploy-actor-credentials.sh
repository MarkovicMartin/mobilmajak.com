#!/usr/bin/env bash
# Nahrání actor skriptů + nastavení secrets na VPS (bez hesel v repu).
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
KEY="${MOBILMAJAK_SSH_KEY:-$REPO_ROOT/.ssh/webmajak_vps/mobilmajak_vps_ed25519}"
ACTOR="/opt/actor/ACTOR_FINALL_WEB_PRODEJE_ALL"
SYMPLIO_SECRETS_LOCAL="${SYMPLIO_SECRETS_LOCAL:-$REPO_ROOT/secrets/mobilmajak-symplio.json}"
SYMPLIO_SECRETS_VPS="/home/webmajak/secrets/mobilmajak-symplio.json"

if [[ ! -f "$SYMPLIO_SECRETS_LOCAL" ]]; then
  echo "Chybí $SYMPLIO_SECRETS_LOCAL – zkopíruj config/secrets-examples/mobilmajak-symplio.example.json → secrets/mobilmajak-symplio.json a vyplň heslo."
  exit 1
fi

echo "==> Symplio secrets na VPS"
ssh -i "$KEY" root@194.182.87.138 "mkdir -p /home/webmajak/secrets && chmod 700 /home/webmajak/secrets"
scp -i "$KEY" "$SYMPLIO_SECRETS_LOCAL" "root@194.182.87.138:${SYMPLIO_SECRETS_VPS}"
ssh -i "$KEY" root@194.182.87.138 "chmod 600 ${SYMPLIO_SECRETS_VPS}"

echo "==> Actor .env na VPS"
scp -i "$KEY" "$REPO_ROOT/scripts/symplio-poznamka-fix/actor-env.example" "root@194.182.87.138:${ACTOR}/.env.example"
ssh -i "$KEY" root@194.182.87.138 bash <<EOF
set -euo pipefail
ACTOR="${ACTOR}"
SYMPLIO_SECRETS_VPS="${SYMPLIO_SECRETS_VPS}"
if [[ ! -f "\$ACTOR/.env" ]]; then
  cp "\$ACTOR/.env.example" "\$ACTOR/.env"
  chmod 600 "\$ACTOR/.env"
fi
grep -q '^SYMPLIO_SECRETS_FILE=' "\$ACTOR/.env" || echo "SYMPLIO_SECRETS_FILE=\$SYMPLIO_SECRETS_VPS" >> "\$ACTOR/.env"
grep -q '^DB_PASSWORD=' "\$ACTOR/.env" || echo "DB_PASSWORD=" >> "\$ACTOR/.env"
echo "Uprav DB_PASSWORD v \$ACTOR/.env pokud chybí."
EOF

echo "==> Skripty actoru"
scp -i "$KEY" \
  "$REPO_ROOT/scripts/symplio-poznamka-fix/main.js" \
  "$REPO_ROOT/scripts/symplio-poznamka-fix/symplio-credentials.js" \
  "$REPO_ROOT/scripts/symplio-poznamka-fix/symplio-login.js" \
  "$REPO_ROOT/scripts/symplio-poznamka-fix/fetch-doklad-notes.js" \
  "$REPO_ROOT/scripts/symplio-poznamka-fix/apply-poznamka-dokladu.js" \
  "$REPO_ROOT/scripts/symplio-poznamka-fix/sync-doklad-notes.js" \
  "$REPO_ROOT/scripts/symplio-poznamka-fix/compare.js" \
  "root@194.182.87.138:${ACTOR}/"

echo "==> Wrapper + cron schedule (Packeta + Symplio poznámky)"
scp -i "$KEY" \
  "$REPO_ROOT/scripts/run-symplio-doklad-notes-safe.sh" \
  "$REPO_ROOT/scripts/packeta-cron-schedule.sh" \
  "root@194.182.87.138:/opt/scripts/"
ssh -i "$KEY" root@194.182.87.138 "chmod +x /opt/scripts/run-symplio-doklad-notes-safe.sh"

echo "==> run-prodeje-actor-safe.sh – načtení .env"
ssh -i "$KEY" root@194.182.87.138 bash <<'EOF'
set -euo pipefail
WRAPPER=/opt/run-prodeje-actor-safe.sh
MARK="# symplio-actor-env"
if [[ -f "$WRAPPER" ]] && ! grep -q "$MARK" "$WRAPPER"; then
  sed -i "/^cd \"\\\$ACTOR_DIR\"/i\\
$MARK\\
if [[ -f \"\\\$ACTOR_DIR/.env\" ]]; then\\
  set -a\\
  # shellcheck disable=SC1091\\
  source \"\\\$ACTOR_DIR/.env\"\\
  set +a\\
fi\\
" "$WRAPPER"
  echo "Patch aplikován na $WRAPPER"
else
  echo "Wrapper už obsahuje env load nebo neexistuje"
fi
EOF

echo "Hotovo."
echo "  Ověř credentials: ssh … 'cd ${ACTOR} && set -a && source .env && set +a && node -e \"require(\\\"./symplio-credentials\\\").loadSymplioCredentials()\"'"
echo "  Nainstaluj cron (Packeta + Symplio poznámky): na VPS spusť scripts/install-packeta-cron.sh"
