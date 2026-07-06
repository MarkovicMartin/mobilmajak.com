#!/bin/bash
# Sourced by finance cron wrappers – WEBAPP_PATH resolution + manage.py on VPS vs local dev.

finance_resolve_webapp() {
  local script_dir="${1:?script_dir required}"
  FINANCE_SCRIPT_DIR="$script_dir"
  FINANCE_REPO_ROOT="$(cd "$script_dir/.." && pwd)"
  FINANCE_BACKEND_RUN="$script_dir/backend-run.sh"

  if [ -n "${WEBAPP_PATH:-}" ]; then
    :
  elif [ -f /home/webmajak/webapp/manage.py ]; then
    WEBAPP_PATH=/home/webmajak/webapp
  elif [ -x "$FINANCE_BACKEND_RUN" ] && [ -f "$FINANCE_REPO_ROOT/backend/manage.py" ]; then
    WEBAPP_PATH=""
  else
    echo "Nelze určit WEBAPP_PATH (nastav WEBAPP_PATH nebo spusť z git repa)" >&2
    return 1
  fi
}

# Echo shell snippet: run manage.py with given args (for embedding in bash -c).
finance_manage_cmd() {
  local manage_args="$*"
  if [ -n "${WEBAPP_PATH:-}" ]; then
    printf "sudo -u webmajak bash -c \"cd '%s' && export DJANGO_SETTINGS_MODULE=webapp.settings_production && '%s/venv/bin/python' manage.py %s\"" \
      "$WEBAPP_PATH" "$WEBAPP_PATH" "$manage_args"
  else
    printf "cd '%s' && '%s' manage.py %s" \
      "$FINANCE_REPO_ROOT" "$FINANCE_BACKEND_RUN" "$manage_args"
  fi
}
