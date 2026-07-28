#!/bin/bash
# Lokální ovládání staging app na VPS.
# Usage: ./scripts/staging-app.sh start|stop|extend|status
# Env: STAGING_IDLE_TTL (default 2h na VPS)
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SSH_KEY="${SSH_KEY:-$REPO_ROOT/.ssh/webmajak_vps/mobilmajak_vps_ed25519}"
TARGET="root@194.182.87.138"
SSH_OPTS=(-i "$SSH_KEY" -o StrictHostKeyChecking=accept-new)
CMD="${1:-}"
REMOTE_CTRL="/opt/scripts/staging-app-control.sh"

case "$CMD" in
  start|stop|extend|status) ;;
  *)
    echo "Usage: $0 start|stop|extend|status"
    echo "  start/extend – zapne staging a naplánuje auto-stop (default 2h)"
    echo "  stop         – vypne staging i timer"
    echo "  STAGING_IDLE_TTL=4h $0 extend"
    exit 1
    ;;
esac

TTL_ENV=""
if [ -n "${STAGING_IDLE_TTL:-}" ]; then
  TTL_ENV="STAGING_IDLE_TTL=${STAGING_IDLE_TTL}"
fi

ssh "${SSH_OPTS[@]}" "$TARGET" "${TTL_ENV} bash $REMOTE_CTRL $CMD"
