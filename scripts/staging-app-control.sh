#!/bin/bash
# Běží na VPS (root). Řídí webmajak-staging + časovač auto-stop.
# Usage: staging-app-control.sh start|stop|extend|status|schedule-stop
# Env: STAGING_IDLE_TTL (default 2h, nebo poslední uložená hodnota)
#   čas: 30m | 1h | 2h | 4h
#   bez limitu: off | 0 | none | unlimited
# Uložená hodnota: /opt/scripts/staging-idle-ttl (jen když je env explicitně nastavené)
set -euo pipefail

SERVICE="webmajak-staging"
TIMER_UNIT="webmajak-staging-autostop"
TTL_STATE="/opt/scripts/staging-idle-ttl"

ttl_disabled() {
  local v
  v="$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')"
  case "$v" in
    0|off|none|unlimited|infinity|inf|disabled) return 0 ;;
    *) return 1 ;;
  esac
}

if [ -n "${STAGING_IDLE_TTL:-}" ]; then
  TTL="$STAGING_IDLE_TTL"
elif [ -r "$TTL_STATE" ]; then
  TTL="$(tr -d '[:space:]' < "$TTL_STATE")"
  if [ -z "$TTL" ]; then
    TTL="2h"
  fi
else
  TTL="2h"
fi

persist_ttl_if_explicit() {
  if [ -n "${STAGING_IDLE_TTL:-}" ]; then
    printf '%s\n' "$TTL" > "$TTL_STATE"
  fi
}

cancel_autostop() {
  systemctl stop "${TIMER_UNIT}.timer" 2>/dev/null || true
  systemctl stop "${TIMER_UNIT}.service" 2>/dev/null || true
  systemctl reset-failed "${TIMER_UNIT}.timer" 2>/dev/null || true
  systemctl reset-failed "${TIMER_UNIT}.service" 2>/dev/null || true
}

schedule_autostop() {
  persist_ttl_if_explicit
  cancel_autostop
  if ttl_disabled "$TTL"; then
    echo "OK: auto-stop vypnutý (staging běží bez časového limitu)"
    return 0
  fi
  # Transient timer: po TTL zastaví staging (nezůstane běžet naprázdno)
  systemd-run \
    --unit="$TIMER_UNIT" \
    --on-active="$TTL" \
    --timer-property=AccuracySec=1min \
    /bin/systemctl stop "$SERVICE"
  echo "OK: auto-stop za $TTL (timer $TIMER_UNIT)"
}

cmd_start() {
  systemctl start "$SERVICE"
  sleep 1
  systemctl is-active "$SERVICE"
  schedule_autostop
}

cmd_stop() {
  cancel_autostop
  systemctl stop "$SERVICE"
  echo "OK: $SERVICE stopped"
}

cmd_extend() {
  if ! systemctl is-active --quiet "$SERVICE"; then
    systemctl start "$SERVICE"
    sleep 1
  fi
  systemctl is-active "$SERVICE"
  schedule_autostop
}

cmd_schedule_stop() {
  # Po deployi: služba už běží (restart), jen (re)nastav timer
  if ! systemctl is-active --quiet "$SERVICE"; then
    systemctl start "$SERVICE"
    sleep 1
  fi
  systemctl is-active "$SERVICE"
  schedule_autostop
}

cmd_status() {
  echo "=== $SERVICE ==="
  systemctl is-active "$SERVICE" 2>&1 || true
  systemctl show "$SERVICE" -p ActiveEnterTimestamp,NRestarts --no-pager 2>/dev/null || true
  echo "=== autostop timer ==="
  if systemctl is-active --quiet "${TIMER_UNIT}.timer" 2>/dev/null; then
    systemctl show "${TIMER_UNIT}.timer" -p NextElapseUSecRealtime,TriggerUSec --no-pager 2>/dev/null || true
    systemctl list-timers "${TIMER_UNIT}.timer" --no-pager 2>/dev/null || true
  else
    echo "(žádný aktivní auto-stop timer)"
  fi
  if ttl_disabled "$TTL"; then
    echo "TTL: $TTL (bez časového limitu)"
  else
    echo "TTL: $TTL"
  fi
  if [ -r "$TTL_STATE" ]; then
    echo "Uloženo: $(tr -d '[:space:]' < "$TTL_STATE") ($TTL_STATE)"
  else
    echo "Uloženo: (žádný soubor, platí výchozí 2h)"
  fi
}

case "${1:-}" in
  start) cmd_start ;;
  stop) cmd_stop ;;
  extend) cmd_extend ;;
  schedule-stop) cmd_schedule_stop ;;
  status) cmd_status ;;
  *)
    echo "Usage: $0 start|stop|extend|schedule-stop|status"
    echo "  STAGING_IDLE_TTL=2h (výchozí) | 30m | 1h | 4h | off"
    echo "  off | 0 | none | unlimited = běží bez auto-stop, dokud se znovu nenastaví čas"
    echo "  Zpět na 2h: STAGING_IDLE_TTL=2h $0 extend"
    exit 1
    ;;
esac
