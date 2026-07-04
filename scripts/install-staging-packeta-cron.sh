#!/bin/bash
# Packeta import cron na staging VPS – stejné rozložení po pobočkách, méně vln.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SSH_KEY="${SSH_KEY:-$REPO_ROOT/.ssh/webmajak_vps/mobilmajak_vps_ed25519}"
TARGET="${STAGING_SSH:-root@194.182.87.138}"
STAGING_PATH="${STAGING_PATH:-/home/webmajak/staging}"
SCRIPT_SRC="$REPO_ROOT/scripts/run-packeta-import-safe.sh"
SCRIPT_DST="/opt/scripts/run-packeta-import-staging-safe.sh"
CRON_FILE="/etc/cron.d/mobilmajak-packeta-import-staging"
CRON_ENV="WEBAPP_PATH=${STAGING_PATH} PACKETA_LOG_FILE=/var/log/packeta-import-staging.log PACKETA_LOCK_FILE=/tmp/packeta-import-staging.lock PACKETA_PID_FILE=/tmp/packeta-import-staging.pid"
STAGGER_MIN="${PACKETA_CRON_STAGGER_MIN:-15}"
AUDIT_STAGGER_MIN="${PACKETA_CRON_AUDIT_STAGGER_MIN:-20}"

if [ ! -f "$SSH_KEY" ]; then
  echo "SSH key not found: $SSH_KEY"
  exit 1
fi

scp -i "$SSH_KEY" -o StrictHostKeyChecking=accept-new "$SCRIPT_SRC" "${TARGET}:/tmp/run-packeta-import-staging-safe.sh"

ssh -i "$SSH_KEY" -o StrictHostKeyChecking=accept-new "$TARGET" bash -s <<EOF
set -euo pipefail
mkdir -p /opt/scripts
mv /tmp/run-packeta-import-staging-safe.sh "$SCRIPT_DST"
chmod +x "$SCRIPT_DST"

_cron_line() {
  local mode=\$1 base_h=\$2 base_m=\$3 stagger=\$4 pid=\$5
  local dow="\${6:-*}"
  local offset=\$(( (pid - 1) * stagger ))
  local total=\$(( base_h * 60 + base_m + offset ))
  local h=\$(( total / 60 ))
  local m=\$(( total % 60 ))
  local env_prefix=""
  if [ "\$mode" = audit ]; then
    env_prefix="PACKETA_AUDIT_DAYS=7 "
  fi
  printf '%d %d * * %s root ${CRON_ENV} %s%s %s %d\n' "\$m" "\$h" "\$dow" "\$env_prefix" "$SCRIPT_DST" "\$mode" "\$pid"
}

{
  echo "# Packeta staging – rozestup ${STAGGER_MIN} min"
  for pid in 1 2 3 4 5 6; do
    _cron_line yesterday 5 0 ${STAGGER_MIN} "\$pid"
  done
  for slot in "12:0" "18:0"; do
    base_h=\${slot%%:*}
    base_m=\${slot##*:}
    for pid in 1 2 3 4 5 6; do
      _cron_line today "\$base_h" "\$base_m" ${STAGGER_MIN} "\$pid"
    done
  done
  for pid in 1 2 3 4 5 6; do
    _cron_line audit 22 0 ${AUDIT_STAGGER_MIN} "\$pid" 0
  done
} > "$CRON_FILE"
chmod 644 "$CRON_FILE"

echo "=== $CRON_FILE ==="
cat "$CRON_FILE"
EOF

echo "Packeta cron na staging nastaven."
