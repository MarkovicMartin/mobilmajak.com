#!/usr/bin/env bash
# Nasazení import-sklad-vydejky.js + env load ve wrapperu.
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
KEY="${MOBILMAJAK_SSH_KEY:-$REPO_ROOT/.ssh/webmajak_vps/mobilmajak_vps_ed25519}"
ACTOR="/opt/actor/ACTOR_FINALL_WEB_PRODEJE_ALL"

scp -i "$KEY" \
  "$REPO_ROOT/scripts/sklad-vydejky/import-sklad-vydejky.js" \
  "root@194.182.87.138:${ACTOR}/"

ssh -i "$KEY" root@194.182.87.138 bash <<'EOF'
set -euo pipefail
WRAPPER=/opt/actor/ACTOR_FINALL_WEB_PRODEJE_ALL/run-sklad-vydejky-actor-safe.sh
MARK="# symplio-actor-env"
if [[ -f "$WRAPPER" ]] && ! grep -q "$MARK" "$WRAPPER"; then
  sed -i "/^cd \"\$ACTOR_DIR\"/i\\
$MARK\\
if [[ -f \"\$ACTOR_DIR/.env\" ]]; then\\
  set -a\\
  # shellcheck disable=SC1091\\
  source \"\$ACTOR_DIR/.env\"\\
  set +a\\
fi\\
export SYMPLIO_SCRIPTS_DIR=\"\$ACTOR_DIR\"\\
" "$WRAPPER"
  echo "Patch wrapper: $WRAPPER"
else
  echo "Wrapper už má env load"
fi
EOF

echo "Hotovo."
