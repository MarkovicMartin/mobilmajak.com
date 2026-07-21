#!/usr/bin/env bash
# Nasazení symplio-pokladna-historie na VPS (/opt/scripts/symplio-pokladna-historie).
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
KEY="${MOBILMAJAK_SSH_KEY:-$REPO_ROOT/.ssh/webmajak_vps/mobilmajak_vps_ed25519}"
TARGET_DIR="/opt/scripts/symplio-pokladna-historie"
PRODEJE_ENV="/opt/actor/ACTOR_FINALL_WEB_PRODEJE_ALL/.env"

ssh -i "$KEY" root@194.182.87.138 "mkdir -p ${TARGET_DIR}/reports"

scp -i "$KEY" \
  "$REPO_ROOT/scripts/symplio-pokladna-historie/fetch-pokladna-xlsx.js" \
  "$REPO_ROOT/scripts/symplio-pokladna-historie/package.json" \
  "$REPO_ROOT/scripts/symplio-pokladna-historie/pokladny.json" \
  "$REPO_ROOT/scripts/symplio-pokladna-historie/actor-env.example" \
  "root@194.182.87.138:${TARGET_DIR}/"

ssh -i "$KEY" root@194.182.87.138 bash <<EOF
set -euo pipefail
TARGET_DIR="${TARGET_DIR}"
PRODEJE_ENV="${PRODEJE_ENV}"
mkdir -p "\$TARGET_DIR/reports"
chmod 755 "\$TARGET_DIR"
if [[ ! -f "\$TARGET_DIR/.env" ]]; then
  cp "\$TARGET_DIR/actor-env.example" "\$TARGET_DIR/.env"
fi
if [[ -f "\$PRODEJE_ENV" ]]; then
  grep '^DB_' "\$PRODEJE_ENV" >> "\$TARGET_DIR/.env" 2>/dev/null || true
  grep '^SYMPLIO_SECRETS_FILE=' "\$PRODEJE_ENV" >> "\$TARGET_DIR/.env" 2>/dev/null || true
fi
grep -q '^SYMPLIO_SCRIPTS_DIR=' "\$TARGET_DIR/.env" || echo 'SYMPLIO_SCRIPTS_DIR=/opt/scripts/symplio-shared' >> "\$TARGET_DIR/.env"
if grep -q '^SYMPLIO_SCRIPTS_DIR=' "\$TARGET_DIR/.env"; then
  sed -i 's|^SYMPLIO_SCRIPTS_DIR=.*|SYMPLIO_SCRIPTS_DIR=/opt/scripts/symplio-shared|' "\$TARGET_DIR/.env"
fi
chmod 600 "\$TARGET_DIR/.env"
cd "\$TARGET_DIR"
if [[ ! -d node_modules ]]; then
  npm install --omit=dev
fi
EOF

echo "Hotovo: \$TARGET_DIR"
