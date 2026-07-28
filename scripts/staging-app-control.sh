#!/bin/bash
# Běží na VPS (root). Řídí webmajak-staging + časovač auto-stop.
# Usage: staging-app-control.sh start|stop|extend|status|schedule-stop
# Env: STAGING_IDLE_TTL (default 2h) – např. 30m, 1h, 2h, 4h
set -euo pipefail

SERVICE="webmajak-staging"
TIMER_UNIT="webmajak-staging-autostop"
TTL="${STAGING_IDLE_TTL:-2h}"

cancel_autostop() {
  systemctl stop "${TIMER_UNIT}.timer" 2>/dev/null || true
  systemctl stop "${TIMER_UNIT}.service" 2>/dev/null || true
  systemctl reset-failed "${TIMER_UNIT}.timer" 2>/dev/null || true
  systemctl reset-failed "${TIMER_UNIT}.service" 2>/dev/null || true
}

schedule_autostop() {
  cancel_autostop
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
  echo "TTL default/current: $TTL"
}

case "${1:-}" in
  start) cmd_start ;;
  stop) cmd_stop ;;
  extend) cmd_extend ;;
  schedule-stop) cmd_schedule_stop ;;
  status) cmd_status ;;
  *)
    echo "Usage: $0 start|stop|extend|schedule-stop|status"
    echo "  STAGING_IDLE_TTL=2h (default) | 30m | 1h | 4h"
    exit 1
    ;;
esac
