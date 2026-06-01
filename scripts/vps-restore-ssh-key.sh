#!/bin/bash
# Obnoví /root/.ssh/authorized_keys a spustí SSH (spustit na VPS jako root ve SPICE).
set -euo pipefail

PUBKEY='ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIPUBYGmXmts5nGh1ihfJFeupGmav/4gIFeYdMGX9Lahe mobilmajak-vps'

mkdir -p /root/.ssh
chmod 700 /root/.ssh
printf '%s\n' "$PUBKEY" > /root/.ssh/authorized_keys
chmod 600 /root/.ssh/authorized_keys
chown root:root /root/.ssh/authorized_keys

echo "=== authorized_keys ==="
cat /root/.ssh/authorized_keys
echo "=== fingerprint ==="
ssh-keygen -lf /root/.ssh/authorized_keys

# SSH služba
systemctl enable ssh 2>/dev/null || systemctl enable sshd 2>/dev/null || true
systemctl restart ssh 2>/dev/null || systemctl restart sshd

# Firewall (pokud běží)
if command -v ufw >/dev/null && ufw status | grep -q 'Status: active'; then
  ufw allow 22/tcp || true
fi

echo "=== port 22 ==="
ss -tlnp | grep ':22' || echo "VAROVÁNÍ: nic neposlouchá na portu 22"

echo "=== sshd_config (výběr) ==="
grep -hE '^(Port|ListenAddress|PermitRootLogin|PubkeyAuthentication|PasswordAuthentication)' \
  /etc/ssh/sshd_config /etc/ssh/sshd_config.d/*.conf 2>/dev/null || true

echo "HOTOVO – z Macu: ssh -i .ssh/webmajak_vps/mobilmajak_vps_ed25519 root@194.182.87.138"
