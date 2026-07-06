#!/bin/bash
# Kontrola frontendu po deployi – HTML musí odkazovat na existující JS/CSS.
# Usage: frontend-smoke-check.sh <base_url> [app_path_on_vps]
set -euo pipefail

BASE_URL="${1:?base_url required}"
APP_PATH="${2:-}"
MIN_MAIN_JS_BYTES="${MIN_MAIN_JS_BYTES:-100000}"

fail() {
  echo "FAIL frontend: $*" >&2
  exit 1
}

check_route_assets() {
  local route="$1"
  local url="${BASE_URL%/}${route}"
  local html
  html=$(curl -sfL "$url" 2>/dev/null) || fail "nelze načíst $url"

  if ! echo "$html" | grep -q '<div id="root">'; then
    fail "$route – chybí SPA root (#root)"
  fi

  local assets
  assets=$(echo "$html" | grep -oE '(/static/js/[^"]+\.js|/static/css/[^"]+\.css)' | sort -u)
  if [ -z "$assets" ]; then
    fail "$route – v HTML nejsou /static/js ani /static/css"
  fi

  local asset
  for asset in $assets; do
    local tmp code size
    tmp=$(mktemp)
    code=$(curl -sfL -o "$tmp" -w "%{http_code}" "${BASE_URL%/}${asset}" 2>/dev/null || echo "000")
    size=$(wc -c < "$tmp" | tr -d ' ')
    rm -f "$tmp"
    if [ "$code" != "200" ]; then
      fail "$route – ${asset} HTTP ${code}"
    fi
    if [[ "$asset" == */main.*.js ]] && [ "$size" -lt "$MIN_MAIN_JS_BYTES" ]; then
      fail "$route – ${asset} podezřele malý (${size} B)"
    fi
  done

  echo "OK frontend assets $route"
}

check_finance_bundle() {
  [ -n "$APP_PATH" ] || return 0

  local ssh_target="${SMOKE_SSH_TARGET:-}"
  local ssh_key="${SMOKE_SSH_KEY:-}"
  [ -n "$ssh_target" ] || return 0

  local ssh_opts=()
  [ -n "$ssh_key" ] && ssh_opts=(-i "$ssh_key" -o StrictHostKeyChecking=accept-new)

  ssh "${ssh_opts[@]}" "$ssh_target" bash -s <<EOF
set -euo pipefail
APP="$APP_PATH"
ENV_FILE="\$APP/frontend/.env.production"
DASH="\$APP/frontend/src/components/Dashboard.js"
BUILD_JS="\$APP/frontend/build/static/js"

if [ ! -f "\$ENV_FILE" ] || ! grep -q '^REACT_APP_FINANCE_ENABLED=1' "\$ENV_FILE" 2>/dev/null; then
  echo "SKIP finance frontend (REACT_APP_FINANCE_ENABLED není 1)"
  exit 0
fi

if [ ! -f "\$DASH" ]; then
  echo "FAIL finance – chybí Dashboard.js" >&2
  exit 1
fi
if ! grep -q 'const FinanceFakturyModule' "\$DASH"; then
  echo "FAIL finance – Dashboard.js nemá const FinanceFakturyModule" >&2
  exit 1
fi
if ! grep -q 'const FinanceModule' "\$DASH"; then
  echo "FAIL finance – Dashboard.js nemá const FinanceModule" >&2
  exit 1
fi
if ! grep -rq 'FinanceFaktury' "\$BUILD_JS" 2>/dev/null; then
  echo "FAIL finance – v build/static/js chybí FinanceFaktury" >&2
  exit 1
fi
if ! grep -rq 'ceka-na-fakturu' "\$BUILD_JS" 2>/dev/null; then
  echo "FAIL finance – v build/static/js chybí API ceka-na-fakturu" >&2
  exit 1
fi
echo "OK finance frontend bundle"
EOF
}

check_route_assets "/"
check_route_assets "/finance/faktury"
check_finance_bundle
echo "OK frontend smoke"
