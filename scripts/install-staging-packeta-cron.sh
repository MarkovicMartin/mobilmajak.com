#!/bin/bash
# Packeta import cron na staging VPS (3× denně). Idempotentní.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SSH_KEY="${SSH_KEY:-$REPO_ROOT/.ssh/webmajak_vps/mobilmajak_vps_ed25519}"
TARGET="${STAGING_SSH:-root@194.182.87.138}"
STAGING_PATH="${STAGING_PATH:-/home/webmajak/staging}"
SCRIPT_SRC="$REPO_ROOT/scripts/run-packeta-import-safe.sh"
SCRIPT_DST="/opt/scripts/run-packeta-import-staging-safe.sh"
CRON_FILE="/etc/cron.d/mobilmajak-packeta-import-staging"
CRON_ENV="WEBAPP_PATH=${STAGING_PATH} PACKETA_LOG_FILE=/var/log/packeta-import-staging.log PACKETA_LOCK_FILE=/tmp/packeta-import-staging.lock PACKETA_PID_FILE=/tmp/packeta-import-staging.pid"

if [ ! -f "$SSH_KEY" ]; then
  echo "SSH key not found: $SSH_KEY"
  exit 1
fi

scp -i "$SSH_KEY" -o StrictHostKeyChecking=accept-new "$SCRIPT_SRC" "${TARGET}:/tmp/run-packeta-import-staging-safe.sh"

ssh -i "$SSH_KEY" -o StrictHostKeyChecking=accept-new "$TARGET" bash -s <<EOF
set -euo pipefail
mkdir -p /opt/scripts
mv /tmp/run-packeta-import-staging-safe.sh "$SCRIPT_DST"
chmod +x "$SCRIPT_DST"

cat > "$CRON_FILE" <<CRON
# Packeta import staging – 3× denně
30 5 * * * root ${CRON_ENV} $SCRIPT_DST month
0 12 * * * root ${CRON_ENV} $SCRIPT_DST recent
0 18 * * * root ${CRON_ENV} $SCRIPT_DST recent
CRON
chmod 644 "$CRON_FILE"

echo "=== $CRON_FILE ==="
cat "$CRON_FILE"
EOF

echo "Packeta cron na staging nastaven."
