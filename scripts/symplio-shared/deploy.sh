#!/usr/bin/env bash
# Nasazení sdíleného Symplio login/credentials na VPS + úprava env ve wrapperech.
# Nespouští actory – jen soubory a SYMPLIO_SCRIPTS_DIR.
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
KEY="${MOBILMAJAK_SSH_KEY:-$REPO_ROOT/.ssh/webmajak_vps/mobilmajak_vps_ed25519}"
TARGET="${SYMPLIO_SSH_TARGET:-root@194.182.87.138}"
SHARED_DIR="/opt/scripts/symplio-shared"
SYMPLIO_SECRETS_VPS="/home/webmajak/secrets/mobilmajak-symplio.json"

PRODEJE_DIR="/opt/actor/ACTOR_FINALL_WEB_PRODEJE_ALL"
VYKUPY_DIR="/opt/actor/ACTOR_VYKUPY"
POKLADNA_DIR="/opt/scripts/symplio-pokladna-historie"

if [[ ! -f "$KEY" ]]; then
  echo "SSH klíč nenalezen: $KEY" >&2
  exit 1
fi

echo "==> Shared modul → ${SHARED_DIR}"
ssh -i "$KEY" -o StrictHostKeyChecking=accept-new "$TARGET" "mkdir -p ${SHARED_DIR}"
scp -i "$KEY" \
  "$REPO_ROOT/scripts/symplio-shared/symplio-credentials.js" \
  "$REPO_ROOT/scripts/symplio-shared/symplio-login.js" \
  "${TARGET}:${SHARED_DIR}/"

echo "==> Actor skripty (bez lokálních credentials kopií)"
scp -i "$KEY" \
  "$REPO_ROOT/scripts/symplio-poznamka-fix/main.js" \
  "$REPO_ROOT/scripts/symplio-poznamka-fix/compare.js" \
  "$REPO_ROOT/scripts/symplio-poznamka-fix/symplio-login.js" \
  "$REPO_ROOT/scripts/symplio-poznamka-fix/symplio-credentials.js" \
  "${TARGET}:${PRODEJE_DIR}/"

scp -i "$KEY" \
  "$REPO_ROOT/scripts/sklad-vydejky/import-sklad-vydejky.js" \
  "${TARGET}:${PRODEJE_DIR}/"

scp -i "$KEY" \
  "$REPO_ROOT/scripts/vykupy-actor/main.js" \
  "$REPO_ROOT/scripts/vykupy-actor/symplio-login.js" \
  "$REPO_ROOT/scripts/vykupy-actor/symplio-credentials.js" \
  "${TARGET}:${VYKUPY_DIR}/"

ssh -i "$KEY" "$TARGET" "mkdir -p ${POKLADNA_DIR}"
scp -i "$KEY" \
  "$REPO_ROOT/scripts/symplio-pokladna-historie/fetch-pokladna-xlsx.js" \
  "${TARGET}:${POKLADNA_DIR}/"

echo "==> SYMPLIO_SCRIPTS_DIR=${SHARED_DIR} ve .env"
ssh -i "$KEY" "$TARGET" bash <<EOF
set -euo pipefail
SHARED_DIR="${SHARED_DIR}"
SECRETS="${SYMPLIO_SECRETS_VPS}"

ensure_env() {
  local env_file="\$1"
  mkdir -p "\$(dirname "\$env_file")"
  if [[ ! -f "\$env_file" ]]; then
    cat > "\$env_file" <<ENV
SYMPLIO_SECRETS_FILE=\$SECRETS
SYMPLIO_SCRIPTS_DIR=\$SHARED_DIR
ENV
  fi
  chmod 600 "\$env_file"
  if grep -q '^SYMPLIO_SCRIPTS_DIR=' "\$env_file"; then
    sed -i "s|^SYMPLIO_SCRIPTS_DIR=.*|SYMPLIO_SCRIPTS_DIR=\$SHARED_DIR|" "\$env_file"
  else
    echo "SYMPLIO_SCRIPTS_DIR=\$SHARED_DIR" >> "\$env_file"
  fi
  grep -q '^SYMPLIO_SECRETS_FILE=' "\$env_file" || echo "SYMPLIO_SECRETS_FILE=\$SECRETS" >> "\$env_file"
}

ensure_env "${PRODEJE_DIR}/.env"
ensure_env "${VYKUPY_DIR}/.env"
ensure_env "${POKLADNA_DIR}/.env"

# Wrapper sklad výdejky – vždy shared
WRAPPER_SKLAD=/opt/run-sklad-vydejky-actor-safe.sh
if [[ -f "\$WRAPPER_SKLAD" ]]; then
  sed -i 's|^export SYMPLIO_SCRIPTS_DIR=.*|export SYMPLIO_SCRIPTS_DIR=${SHARED_DIR}|' "\$WRAPPER_SKLAD" || true
  if ! grep -q 'SYMPLIO_SCRIPTS_DIR=' "\$WRAPPER_SKLAD"; then
    echo "export SYMPLIO_SCRIPTS_DIR=${SHARED_DIR}" >> "\$WRAPPER_SKLAD"
  fi
fi

# Fallback By resolve, pokud cwd actoru nemá selenium (login už nepoužívá until.*).
mkdir -p "\$SHARED_DIR/node_modules"
LIVE_SELENIUM="${PRODEJE_DIR}/node_modules/selenium-webdriver"
if [[ -d "\$LIVE_SELENIUM" ]]; then
  rm -f "\$SHARED_DIR/node_modules/selenium-webdriver"
  ln -s "\$LIVE_SELENIUM" "\$SHARED_DIR/node_modules/selenium-webdriver"
fi

echo "Ověření shared:"
ls -la "\$SHARED_DIR"
node -e "require('${SHARED_DIR}/symplio-credentials'); require('${SHARED_DIR}/symplio-login'); console.log('OK require')"
EOF

echo ""
echo "Hotovo. Ruční ověření na VPS:"
echo "  # prodeje"
echo "  cd ${PRODEJE_DIR} && set -a && source .env && set +a && node -e \"require('./symplio-login').loginSymplio\""
echo "  # výkupy / výdejky / pokladna – cron nebo jednorázový běh wrapperů"
echo ""
echo "Rotace hesla: jeden soubor ${SYMPLIO_SECRETS_VPS} (viz docs/secrets-setup.md)."
