#!/usr/bin/env bash
# Jednorázově: privátní git repozitář pro sledování záloh (manifesty + návod, NE dumpy).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKUP_ROOT="${MOBILMAJAK_BACKUP_ROOT:-$REPO_ROOT/../mobilmajak-backups}"
GIT_REMOTE="${1:-}"

mkdir -p "$BACKUP_ROOT"

if [[ ! -d "$BACKUP_ROOT/.git" ]]; then
  git -C "$BACKUP_ROOT" init
  git -C "$BACKUP_ROOT" branch -M main 2>/dev/null || true
fi

cat > "$BACKUP_ROOT/.gitignore" <<'GI'
# Velké archivy a citlivé soubory – zůstávají jen lokálně na disku
*.tar.gz
*.sql
*.sql.gz
local-secrets/
**/local-secrets/
*.env
*.pem
*_ed25519
# Složky s kompletní zálohou (YYYYMMDD-HHMMSS) – do gitu jen kopie v manifests/
[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]-*/
latest
GI

cat > "$BACKUP_ROOT/README.md" <<'MD'
# mobilmajak-backups (off-site)

Privátní repozitář pro **manifesty** záloh. Samotné `.tar.gz` a MySQL dumpy zůstávají v podsložkách `YYYYMMDD-HHMMSS/` a do gitu se necommitují (velikost + hesla).

## Vytvoření zálohy

```bash
cd mobilmajak.com
./scripts/backup-full-server.sh
```

## Sync manifestů do gitu

```bash
./scripts/backup-sync-manifests-to-git.sh
```

## Obnova

Viz `latest/RESTORE.md` nebo `*/RESTORE.md` v konkrétní záloze.
MD

if [[ -n "$GIT_REMOTE" ]]; then
  git -C "$BACKUP_ROOT" remote remove origin 2>/dev/null || true
  git -C "$BACKUP_ROOT" remote add origin "$GIT_REMOTE"
  echo "Remote: $GIT_REMOTE"
  echo "Pak: git -C $BACKUP_ROOT push -u origin main"
fi

echo "Inicializováno: $BACKUP_ROOT"
echo "Doplňte remote: ./scripts/backup-init-offsite-git.sh git@github.com:VAS-UCET/mobilmajak-backups.git"
