#!/bin/bash
# Zabije osiřelé Selenium Chrome/chromedriver (PPID=1) a volitelně staré temp složky.
# Bezpečné i během běžícího actora: aktivní chromedriver má parent = node, ne init.
#
# Usage:
#   selenium-chrome-cleanup.sh              # orphans + temp dirs older than 60 min
#   selenium-chrome-cleanup.sh --orphans-only
#   selenium-chrome-cleanup.sh --quiet

set -u

ORPHANS_ONLY=false
QUIET=false
for arg in "$@"; do
  case "$arg" in
    --orphans-only) ORPHANS_ONLY=true ;;
    --quiet) QUIET=true ;;
  esac
done

log() {
  if [ "$QUIET" = false ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $*"
  fi
}

kill_tree() {
  local pid="$1"
  [ -n "$pid" ] || return 0
  [ -d "/proc/$pid" ] || return 0
  # children first
  local child
  for child in $(pgrep -P "$pid" 2>/dev/null || true); do
    kill_tree "$child"
  done
  kill -TERM "$pid" 2>/dev/null || true
  sleep 0.2
  if [ -d "/proc/$pid" ]; then
    kill -KILL "$pid" 2>/dev/null || true
  fi
  return 0
}

is_ppid1() {
  local pid="$1"
  local ppid
  ppid=$(ps -o ppid= -p "$pid" 2>/dev/null | tr -d ' ')
  [ "$ppid" = "1" ]
}

killed=0

# 1) Orphan chromedriver → zabít celý strom (chrome děti)
while read -r pid; do
  [ -n "$pid" ] || continue
  is_ppid1 "$pid" || continue
  log "Killing orphan chromedriver PID $pid (+ children)"
  kill_tree "$pid"
  killed=$((killed + 1))
done < <(pgrep -f '[c]hromedriver.*--port=' || true)

# 2) Orphan headless Chrome z WebDriveru (chromedriver už mrtvý)
while read -r pid; do
  [ -n "$pid" ] || continue
  is_ppid1 "$pid" || continue
  # jen automation / webdriver session, ne náhodný browser uživatele
  if tr '\0' '\n' < "/proc/$pid/cmdline" 2>/dev/null | grep -qE 'test-type=webdriver|enable-automation|headless'; then
    log "Killing orphan chrome PID $pid"
    kill_tree "$pid"
    killed=$((killed + 1))
  fi
done < <(pgrep -f '[g]oogle-chrome|[c]hromium' || true)

# crashpad handlery s PPID 1 po smrti chrome
while read -r pid; do
  [ -n "$pid" ] || continue
  is_ppid1 "$pid" || continue
  if tr '\0' '\n' < "/proc/$pid/cmdline" 2>/dev/null | grep -q 'chrome_crashpad_handler'; then
    kill -KILL "$pid" 2>/dev/null || true
    killed=$((killed + 1))
  fi
done < <(pgrep -f '[c]hrome_crashpad_handler' || true)

if [ "$ORPHANS_ONLY" = false ]; then
  before=$(find /tmp -name '.org.chromium.Chromium.*' -type d 2>/dev/null | wc -l | tr -d ' ')
  find /tmp -name '.org.chromium.Chromium.*' -type d -mmin +60 -exec rm -rf {} + 2>/dev/null || true
  after=$(find /tmp -name '.org.chromium.Chromium.*' -type d 2>/dev/null | wc -l | tr -d ' ')
  log "Temp Chromium dirs: before=$before after=$after (removed age>60m)"
fi

log "Orphan selenium cleanup done (kill actions≈$killed)"
exit 0
