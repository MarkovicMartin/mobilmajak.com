#!/bin/bash
# Deploy na https://staging.mobilmajak.com
# Usage: ./scripts/deploy-staging.sh [--skip-build]
#
# Frontend build běží na VPS (Node 18), pokud lokálně nemáte npm.

set -euo pipefail

SKIP_BUILD=false
for arg in "$@"; do
  case "$arg" in
    --skip-build) SKIP_BUILD=true ;;
    *) echo "Unknown option: $arg"; exit 1 ;;
  esac
done

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SSH_KEY="${SSH_KEY:-$REPO_ROOT/.ssh/webmajak_vps/mobilmajak_vps_ed25519}"
TARGET="root@194.182.87.138"
STAGING_PATH="/home/webmajak/staging"
BACKEND_ARCHIVE="/tmp/mobilmajak-staging-backend.tar.gz"
FRONTEND_ARCHIVE="/tmp/mobilmajak-staging-frontend-src.tar.gz"
SSH_OPTS=(-i "$SSH_KEY" -o StrictHostKeyChecking=accept-new)

if [ ! -f "$SSH_KEY" ]; then
  echo "SSH key not found: $SSH_KEY"
  exit 1
fi

ssh_cmd() { ssh "${SSH_OPTS[@]}" "$TARGET" "$@"; }
scp_cmd() { scp "${SSH_OPTS[@]}" "$@"; }

echo "=== Staging deploy -> https://staging.mobilmajak.com ==="
echo "SSH key: $SSH_KEY"
echo ""

echo "[1/5] Backend..."
rm -f "$BACKEND_ARCHIVE"
tar -czf "$BACKEND_ARCHIVE" -C "$REPO_ROOT/backend" \
  --exclude=venv --exclude=__pycache__ --exclude='*.pyc' \
  --exclude=logs --exclude=media --exclude=staticfiles \
  --exclude=.env .
scp_cmd "$BACKEND_ARCHIVE" "${TARGET}:/tmp/staging-backend.tar.gz"
ssh_cmd "cd $STAGING_PATH && tar -xzf /tmp/staging-backend.tar.gz && rm -f /tmp/staging-backend.tar.gz && chown -R webmajak:webmajak $STAGING_PATH"
rm -f "$BACKEND_ARCHIVE"
echo "  OK backend"

echo "[2/5] Frontend sources..."
rm -f "$FRONTEND_ARCHIVE"
tar -czf "$FRONTEND_ARCHIVE" -C "$REPO_ROOT/frontend" --exclude=node_modules --exclude=build .
scp_cmd "$FRONTEND_ARCHIVE" "${TARGET}:/tmp/staging-frontend-src.tar.gz"
ssh_cmd "mkdir -p ${STAGING_PATH}/frontend && cd ${STAGING_PATH}/frontend && tar -xzf /tmp/staging-frontend-src.tar.gz && rm -f /tmp/staging-frontend-src.tar.gz && chown -R webmajak:webmajak ${STAGING_PATH}/frontend"
rm -f "$FRONTEND_ARCHIVE"
echo "  OK frontend sources"

if [ "$SKIP_BUILD" = true ]; then
  echo "[3/5] Skip frontend build (--skip-build)"
else
  echo "[3/5] npm ci && build on server..."
  scp_cmd "$REPO_ROOT/scripts/frontend-build-vps.sh" "${TARGET}:/tmp/frontend-build-vps.sh"
  ssh_cmd "sed -i 's/\r$//' /tmp/frontend-build-vps.sh; sudo -u webmajak bash /tmp/frontend-build-vps.sh ${STAGING_PATH}/frontend; rm -f /tmp/frontend-build-vps.sh"
fi

echo "[4/5] Post-deploy..."
scp_cmd "$REPO_ROOT/scripts/staging-post-deploy.sh" "${TARGET}:/tmp/staging-post-deploy.sh"
ssh_cmd "sed -i 's/\r$//' /tmp/staging-post-deploy.sh; bash /tmp/staging-post-deploy.sh; rm -f /tmp/staging-post-deploy.sh; chmod -R a+rX ${STAGING_PATH}/frontend/build/static 2>/dev/null || true; systemctl reload nginx"

echo "[5/5] Smoke test..."
"$REPO_ROOT/scripts/post-deploy-smoke.sh" staging
echo ""
echo "Done. https://staging.mobilmajak.com/"
echo "Staging workery: auto-stop za ${STAGING_IDLE_TTL:-2h}. Ručně: ./scripts/staging-app.sh stop|extend|status"
