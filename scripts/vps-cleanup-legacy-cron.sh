#!/usr/bin/env bash
# Odstraní zastaralé cron joby na produkčním VPS.
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
KEY="${MOBILMAJAK_SSH_KEY:-$REPO_ROOT/.ssh/webmajak_vps/mobilmajak_vps_ed25519}"

ssh -i "$KEY" root@194.182.87.138 bash <<'REMOTE'
set -euo pipefail

echo "==> Odstranění staging Packeta cronu"
rm -f /etc/cron.d/mobilmajak-packeta-import-staging

echo "==> Odstranění web-prodeje-importer cronu"
rm -f /etc/cron.d/web-prodeje-importer

echo "==> Odstranění cron_analytics z root crontabu"
TMP=/tmp/crontab-root-clean.tmp
crontab -l 2>/dev/null | grep -v 'cron_analytics.sh' > "$TMP" || true
crontab "$TMP"
rm -f "$TMP"

echo "==> Zbývající cron.d"
ls -la /etc/cron.d/mobilmajak* 2>/dev/null || true
echo "==> Root crontab"
crontab -l 2>/dev/null || true
echo "==> webmajak crontab"
crontab -u webmajak -l 2>/dev/null || true
REMOTE

echo "Legacy cron cleanup hotovo."
