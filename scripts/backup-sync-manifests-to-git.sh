#!/usr/bin/env bash
# Zkopíruje manifest.json + RESTORE.md z posledních záloh do git repa (bez tar.gz).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKUP_ROOT="${MOBILMAJAK_BACKUP_ROOT:-$REPO_ROOT/../mobilmajak-backups}"

if [[ ! -d "$BACKUP_ROOT/.git" ]]; then
  echo "Nejdřív: ./scripts/backup-init-offsite-git.sh [git-remote-url]"
  exit 1
fi

LATEST="$(readlink -f "$BACKUP_ROOT/latest" 2>/dev/null || readlink "$BACKUP_ROOT/latest" 2>/dev/null || true)"
if [[ -n "$LATEST" && -f "$LATEST/manifest.json" ]]; then
  cp "$LATEST/manifest.json" "$BACKUP_ROOT/latest-manifest.json"
  cp "$LATEST/RESTORE.md" "$BACKUP_ROOT/RESTORE-latest.md"
fi

# Poslední 3 zálohy – jen malé soubory
count=0
for dir in $(ls -1dt "$BACKUP_ROOT"/[0-9]* 2>/dev/null | head -3); do
  stamp="$(basename "$dir")"
  mkdir -p "$BACKUP_ROOT/manifests/$stamp"
  [[ -f "$dir/manifest.json" ]] && cp "$dir/manifest.json" "$BACKUP_ROOT/manifests/$stamp/"
  [[ -f "$dir/repo-git-HEAD.txt" ]] && cp "$dir/repo-git-HEAD.txt" "$BACKUP_ROOT/manifests/$stamp/"
  count=$((count + 1))
done

git -C "$BACKUP_ROOT" add -A
git -C "$BACKUP_ROOT" status
if git -C "$BACKUP_ROOT" diff --cached --quiet; then
  echo "Žádná změna k commitu."
  exit 0
fi

git -C "$BACKUP_ROOT" commit -m "backup manifests $(date +%Y-%m-%d)"
echo "Commit hotový. Push: git -C $BACKUP_ROOT push"
