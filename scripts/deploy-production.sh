#!/bin/bash
# Deploy na https://mobilmajak.com (produkce)
# Usage: ./scripts/deploy-production.sh [--skip-build]
#
# Frontend build běží na VPS (Node), pokud lokálně nemáte npm.

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
PROD_PATH="/home/webmajak/webapp"
BACKEND_ARCHIVE="/tmp/mobilmajak-production-backend.tar.gz"
FRONTEND_ARCHIVE="/tmp/mobilmajak-production-frontend-src.tar.gz"
SSH_OPTS=(-i "$SSH_KEY" -o StrictHostKeyChecking=accept-new)

if [ ! -f "$SSH_KEY" ]; then
  echo "SSH key not found: $SSH_KEY"
  exit 1
fi

ssh_cmd() { ssh "${SSH_OPTS[@]}" "$TARGET" "$@"; }
scp_cmd() { scp "${SSH_OPTS[@]}" "$@"; }

echo "=== Production deploy -> https://mobilmajak.com ==="
echo "SSH key: $SSH_KEY"
echo ""

echo "[1/5] Backend..."
rm -f "$BACKEND_ARCHIVE"
tar -czf "$BACKEND_ARCHIVE" -C "$REPO_ROOT/backend" \
  --exclude=venv --exclude=__pycache__ --exclude='*.pyc' \
  --exclude=logs --exclude=media --exclude=staticfiles \
  --exclude=.env .
scp_cmd "$BACKEND_ARCHIVE" "${TARGET}:/tmp/production-backend.tar.gz"
ssh_cmd "cd $PROD_PATH && tar -xzf /tmp/production-backend.tar.gz && rm -f /tmp/production-backend.tar.gz && chown -R webmajak:webmajak $PROD_PATH"
rm -f "$BACKEND_ARCHIVE"
echo "  OK backend"

echo "[2/5] Frontend sources..."
rm -f "$FRONTEND_ARCHIVE"
tar -czf "$FRONTEND_ARCHIVE" -C "$REPO_ROOT/frontend" --exclude=node_modules --exclude=build .
scp_cmd "$FRONTEND_ARCHIVE" "${TARGET}:/tmp/production-frontend-src.tar.gz"
ssh_cmd "mkdir -p ${PROD_PATH}/frontend && cd ${PROD_PATH}/frontend && tar -xzf /tmp/production-frontend-src.tar.gz && rm -f /tmp/production-frontend-src.tar.gz && chown -R webmajak:webmajak ${PROD_PATH}/frontend"
rm -f "$FRONTEND_ARCHIVE"
echo "  OK frontend sources"

if [ "$SKIP_BUILD" = true ]; then
  echo "[3/5] Skip frontend build (--skip-build)"
else
  echo "[3/5] npm ci && build on server..."
  scp_cmd "$REPO_ROOT/scripts/frontend-build-vps.sh" "${TARGET}:/tmp/frontend-build-vps.sh"
  ssh_cmd "sed -i 's/\r$//' /tmp/frontend-build-vps.sh; sudo -u webmajak bash /tmp/frontend-build-vps.sh ${PROD_PATH}/frontend; rm -f /tmp/frontend-build-vps.sh"
fi

echo "[4/5] Post-deploy..."
scp_cmd "$REPO_ROOT/scripts/production-post-deploy.sh" "${TARGET}:/tmp/production-post-deploy.sh"
ssh_cmd "sed -i 's/\r$//' /tmp/production-post-deploy.sh; bash /tmp/production-post-deploy.sh; rm -f /tmp/production-post-deploy.sh; chmod -R a+rX ${PROD_PATH}/frontend/build/static 2>/dev/null || true; systemctl reload nginx"

echo "[5/5] Smoke test..."
"$REPO_ROOT/scripts/post-deploy-smoke.sh" production
echo ""
echo "Done. https://mobilmajak.com/"
