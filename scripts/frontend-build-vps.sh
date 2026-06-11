#!/bin/bash
# Frontend build on VPS (volá deploy-staging / deploy-production přes SSH).
set -euo pipefail
FRONTEND_DIR="${1:?Usage: frontend-build-vps.sh /path/to/frontend}"
cd "$FRONTEND_DIR"
npm ci --prefer-offline --no-audit
npx --yes update-browserslist-db@latest
CI=false npm run build
