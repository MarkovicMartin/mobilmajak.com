#!/usr/bin/env bash
# Nasazení výkupy actoru na VPS + .env se Symplio credentials.
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
KEY="${MOBILMAJAK_SSH_KEY:-$REPO_ROOT/.ssh/webmajak_vps/mobilmajak_vps_ed25519}"
ACTOR="/opt/actor/ACTOR_VYKUPY"
SYMPLIO_SECRETS_VPS="/home/webmajak/secrets/mobilmajak-symplio.json"
PRODEJE_ENV="/opt/actor/ACTOR_FINALL_WEB_PRODEJE_ALL/.env"

echo "==> Skripty výkupy actoru"
scp -i "$KEY" \
  "$REPO_ROOT/scripts/vykupy-actor/main.js" \
  "$REPO_ROOT/scripts/vykupy-actor/symplio-credentials.js" \
  "$REPO_ROOT/scripts/vykupy-actor/symplio-login.js" \
  "root@194.182.87.138:${ACTOR}/"

echo "==> .env pro výkupy actor (reuse z prodejního actoru)"
ssh -i "$KEY" root@194.182.87.138 bash <<EOF
set -euo pipefail
ACTOR="${ACTOR}"
PRODEJE_ENV="${PRODEJE_ENV}"
SYMPLIO_SECRETS_VPS="${SYMPLIO_SECRETS_VPS}"
if [[ -f "\$PRODEJE_ENV" ]]; then
  cp "\$PRODEJE_ENV" "\$ACTOR/.env"
else
  cat > "\$ACTOR/.env" <<ENV
SYMPLIO_SECRETS_FILE=\$SYMPLIO_SECRETS_VPS
DB_HOST=db.dw300.webglobe.com
DB_USER=multi_724223
DB_NAME=multi_724223
DB_PASSWORD=
ENV
fi
chmod 600 "\$ACTOR/.env"
grep -q '^SYMPLIO_SECRETS_FILE=' "\$ACTOR/.env" || echo "SYMPLIO_SECRETS_FILE=\$SYMPLIO_SECRETS_VPS" >> "\$ACTOR/.env"
EOF

echo "==> run-vykupy-actor.sh – načtení .env"
ssh -i "$KEY" root@194.182.87.138 bash <<'EOF'
set -euo pipefail
WRAPPER=/opt/run-vykupy-actor.sh
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
