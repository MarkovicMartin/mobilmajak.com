#!/usr/bin/env bash
# Local full-stack: Django (MySQL via backend/.env) + production build + browser
# Usage: ./scripts/run-local.sh
#        ./scripts/run-local.sh --rebuild

set -euo pipefail

REBUILD=0
BACKEND_PORT=8000
FRONTEND_PORT=8001

while [[ $# -gt 0 ]]; do
  case "$1" in
    --rebuild|-Rebuild) REBUILD=1; shift ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND="$REPO_ROOT/backend"
FRONTEND="$REPO_ROOT/frontend"
BUILD_DIR="$FRONTEND/build"
ENV_FILE="$BACKEND/.env"
ENV_EXAMPLE="$BACKEND/.env.example"
BACKEND_URL="http://127.0.0.1:$BACKEND_PORT"
FRONTEND_URL="http://localhost:$FRONTEND_PORT"

step() { printf '\n==> %s\n' "$1"; }
ok() { printf 'OK  %s\n' "$1"; }
warn() { printf '!!  %s\n' "$1"; }

find_node() {
  if command -v node >/dev/null 2>&1; then
    command -v node
    return
  fi
  local cursor_node="/Applications/Cursor.app/Contents/Resources/app/resources/helpers/node"
  if [[ -x "$cursor_node" ]]; then
    echo "$cursor_node"
    return
  fi
  echo "ERROR: node not in PATH and Cursor node not found at $cursor_node" >&2
  exit 1
}

find_python() {
  # shellcheck source=lib/backend-venv.sh
  source "$REPO_ROOT/scripts/lib/backend-venv.sh"
  ensure_backend_venv
  echo "$BACKEND_PYTHON"
}

stop_port() {
  local port=$1
  if command -v lsof >/dev/null 2>&1; then
    lsof -ti tcp:"$port" -sTCP:LISTEN 2>/dev/null | xargs kill -9 2>/dev/null || true
  fi
}

wait_http() {
  local url=$1 max=${2:-90} i=0
  while (( i < max )); do
    if curl -sf -o /dev/null --max-time 5 "$url"; then
      return 0
    fi
    sleep 2
    ((i += 2)) || true
  done
  return 1
}

ensure_env() {
  if [[ ! -f "$ENV_EXAMPLE" ]]; then
    echo "Missing $ENV_EXAMPLE" >&2
    exit 1
  fi
  if [[ ! -f "$ENV_FILE" ]]; then
    cp "$ENV_EXAMPLE" "$ENV_FILE"
    warn "Created $ENV_FILE from .env.example"
  fi
  if [[ -n "${DB_PASSWORD:-}" ]]; then
  if grep -q '^\s*DB_PASSWORD=' "$ENV_FILE"; then
      sed -i '' "s|^\s*DB_PASSWORD=.*|DB_PASSWORD=$DB_PASSWORD|" "$ENV_FILE" 2>/dev/null || \
        sed -i "s|^\s*DB_PASSWORD=.*|DB_PASSWORD=$DB_PASSWORD|" "$ENV_FILE"
    else
      printf '\nDB_PASSWORD=%s\n' "$DB_PASSWORD" >> "$ENV_FILE"
    fi
    ok 'DB_PASSWORD from environment variable'
  fi
  if ! grep -q '^\s*DB_PASSWORD=.\+' "$ENV_FILE"; then
    cat >&2 <<EOF

backend/.env is missing DB_PASSWORD (MySQL).
Set it in backend/.env or run:
  DB_PASSWORD='your-password' ./scripts/run-local.sh
EOF
    exit 1
  fi
}

ensure_frontend_build() {
  local node npm_cmd
  node="$(find_node)"
  if command -v npm >/dev/null 2>&1; then
    npm_cmd=npm
  else
    npm_cmd() {
      if [[ "$1" == "run" && "$2" == "build" ]]; then
        "$node" "$FRONTEND/node_modules/react-scripts/bin/react-scripts.js" build
      elif [[ "$1" == "run" && "$2" == "serve:build" ]]; then
        API_PROXY="$BACKEND_URL" PORT="$FRONTEND_PORT" "$node" "$FRONTEND/scripts/serve-build.js"
      else
        echo "npm not in PATH; unsupported: npm $*" >&2
        exit 1
      fi
    }
  fi

  if [[ ! -d "$FRONTEND/node_modules" ]]; then
    step 'Installing frontend dependencies (npm install) ...'
    if command -v npm >/dev/null 2>&1; then
      (cd "$FRONTEND" && npm install)
    else
      echo "ERROR: node_modules missing and npm not in PATH. Install Node/npm or copy node_modules." >&2
      exit 1
    fi
  fi

  if [[ "$REBUILD" -eq 1 || ! -f "$BUILD_DIR/index.html" ]]; then
    step 'Building frontend ...'
    if command -v npm >/dev/null 2>&1; then
      (cd "$FRONTEND" && npm run build)
    else
      (cd "$FRONTEND" && "$node" node_modules/react-scripts/bin/react-scripts.js build)
    fi
  else
    ok 'Using existing frontend/build (pass --rebuild for fresh build)'
  fi

  export NODE_BIN="$node"
  export FRONTEND_NPM_CMD=npm_cmd
}

DJANGO_PID=""
FRONTEND_PID=""

cleanup() {
  step 'Stopping processes ...'
  [[ -n "$DJANGO_PID" ]] && kill "$DJANGO_PID" 2>/dev/null || true
  [[ -n "$FRONTEND_PID" ]] && kill "$FRONTEND_PID" 2>/dev/null || true
  stop_port "$BACKEND_PORT"
  stop_port "$FRONTEND_PORT"
}
trap cleanup EXIT INT TERM

printf '\nMOBILMAJAK - local test (build + DB + API)\n'
printf 'Repo: %s\n' "$REPO_ROOT"

NODE="$(find_node)"
PYTHON="$(find_python)"

ensure_env
step 'Checking Django ...'
"$PYTHON" "$BACKEND/manage.py" check --database default
ensure_frontend_build

step "Freeing ports $BACKEND_PORT and $FRONTEND_PORT ..."
stop_port "$BACKEND_PORT"
stop_port "$FRONTEND_PORT"
sleep 1

step "Starting Django API on port $BACKEND_PORT ..."
"$PYTHON" "$BACKEND/manage.py" runserver "127.0.0.1:$BACKEND_PORT" --noreload &
DJANGO_PID=$!

if ! wait_http "$BACKEND_URL/health/"; then
  echo "Backend at $BACKEND_URL not responding. Check DB_PASSWORD and network." >&2
  exit 1
fi
ok "Backend running ($BACKEND_URL)"

step "Starting frontend build on port $FRONTEND_PORT ..."
if command -v npm >/dev/null 2>&1; then
  (cd "$FRONTEND" && API_PROXY="$BACKEND_URL" PORT="$FRONTEND_PORT" npm run serve:build) &
else
  (cd "$FRONTEND" && API_PROXY="$BACKEND_URL" PORT="$FRONTEND_PORT" "$NODE" scripts/serve-build.js) &
fi
FRONTEND_PID=$!

if ! wait_http "$FRONTEND_URL/"; then
  echo "Frontend at $FRONTEND_URL not responding." >&2
  exit 1
fi
ok "Frontend running ($FRONTEND_URL)"

printf '\n========================================\n'
printf '  App:       %s\n' "$FRONTEND_URL"
printf '  API/DB:    %s  (MySQL via backend/.env)\n' "$BACKEND_URL"
printf '  Stop:      Ctrl+C in this window\n'
printf '========================================\n\n'

if command -v open >/dev/null 2>&1; then
  open "$FRONTEND_URL" || true
fi

wait "$DJANGO_PID" "$FRONTEND_PID" 2>/dev/null || wait
