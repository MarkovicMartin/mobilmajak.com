#!/bin/bash
# Frontend build on VPS (volá deploy-staging / deploy-production přes SSH).
set -euo pipefail
FRONTEND_DIR="${1:?Usage: frontend-build-vps.sh /path/to/frontend}"

LOCK_FILE="/tmp/mobilmajak-frontend-build.lock"
exec 9>"$LOCK_FILE"
if ! flock -w 900 9; then
  echo "Timed out waiting for frontend build lock" >&2
  exit 1
fi

WORK=$(mktemp -d /tmp/mobilmajak-fe-build.XXXXXX)
cleanup() { rm -rf "$WORK"; }
trap cleanup EXIT

cd "$WORK"
for item in package.json package-lock.json public src scripts; do
  cp -a "$FRONTEND_DIR/$item" .
done
if [ -f "$FRONTEND_DIR/.env.production" ]; then
  cp -a "$FRONTEND_DIR/.env.production" .
fi

npm ci --no-audit
npx --yes update-browserslist-db@latest || true
CI=false DISABLE_ESLINT_PLUGIN=true npm run build

rm -rf "$FRONTEND_DIR/build"
cp -a build "$FRONTEND_DIR/build"
chown -R webmajak:webmajak "$FRONTEND_DIR/build"
