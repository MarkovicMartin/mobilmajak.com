#!/usr/bin/env bash
# Kompletní off-site záloha: actoři, webapp/staging na VPS, MySQL dump, server config, git snapshot.
# Výstup: ../mobilmajak-backups/YYYYMMDD-HHMMSS/ (mimo git – obsahuje hesla v dumpu a .env)
#
#   ./scripts/backup-full-server.sh
#   MOBILMAJAK_BACKUP_ROOT=~/Archiv/mobilmajak ./scripts/backup-full-server.sh
#   ./scripts/backup-full-server.sh --with-node-modules
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
KEY="${MOBILMAJAK_SSH_KEY:-$REPO_ROOT/.ssh/webmajak_vps/mobilmajak_vps_ed25519}"
HOST="${MOBILMAJAK_SSH_HOST:-root@194.182.87.138}"
BACKUP_ROOT="${MOBILMAJAK_BACKUP_ROOT:-$REPO_ROOT/../mobilmajak-backups}"
STAMP="$(date +%Y%m%d-%H%M%S)"
DEST="$BACKUP_ROOT/$STAMP"
REMOTE_TMP="/opt/backups/full-backup-$STAMP"

INCLUDE_NODE_MODULES=0
for arg in "$@"; do
  case "$arg" in
    --with-node-modules) INCLUDE_NODE_MODULES=1 ;;
    -h|--help)
      grep '^#' "$0" | head -8 | sed 's/^# \?//'
      exit 0
      ;;
  esac
done

if [[ ! -f "$KEY" ]]; then
  echo "Chybí SSH klíč: $KEY"
  exit 1
fi

SSH=(ssh -i "$KEY" -o ConnectTimeout=15 "$HOST")
SCP=(scp -i "$KEY")

TAR_EXCLUDE_ACTOR=(--exclude=node_modules)
TAR_EXCLUDE_APP=(
  --exclude=node_modules
  --exclude=venv
  --exclude=staticfiles
  --exclude=frontend/build
  --exclude=frontend/node_modules
  --exclude=.git
)
if [[ "$INCLUDE_NODE_MODULES" -eq 1 ]]; then
  TAR_EXCLUDE_ACTOR=()
  TAR_EXCLUDE_APP=(--exclude=.git)
fi

mkdir -p "$DEST"
echo "=== MOBILMAJAK full backup ==="
echo "Cíl: $DEST"

"${SSH[@]}" "mkdir -p $REMOTE_TMP"

echo "[1/6] Actoři /opt/actor..."
EX_ACTOR=""
[[ ${#TAR_EXCLUDE_ACTOR[@]} -gt 0 ]] && EX_ACTOR="${TAR_EXCLUDE_ACTOR[*]}"
"${SSH[@]}" "tar -czf $REMOTE_TMP/actors-all.tar.gz $EX_ACTOR -C /opt actor"

echo "[2/6] webapp + staging..."
EX_APP=""
[[ ${#TAR_EXCLUDE_APP[@]} -gt 0 ]] && EX_APP="${TAR_EXCLUDE_APP[*]}"
"${SSH[@]}" "tar -czf $REMOTE_TMP/webapp-production.tar.gz $EX_APP -C /home/webmajak webapp"
"${SSH[@]}" "tar -czf $REMOTE_TMP/webapp-staging.tar.gz $EX_APP -C /home/webmajak staging"

echo "[3/6] Server config..."
"${SSH[@]}" bash <<REMOTE
set -euo pipefail
TMP="$REMOTE_TMP"
mkdir -p "\$TMP/server-config"
crontab -l > "\$TMP/server-config/crontab-root.txt" 2>/dev/null || true
crontab -u webmajak -l > "\$TMP/server-config/crontab-webmajak.txt" 2>/dev/null || true
cp -a /etc/nginx/sites-enabled "\$TMP/server-config/" 2>/dev/null || true
cp /opt/run-prodeje-actor-safe.sh /opt/run-vykupy-actor.sh /opt/CISTIC_TEMP_SLOZKY.sh "\$TMP/server-config/" 2>/dev/null || true
tar -czf "\$TMP/server-config.tar.gz" -C "\$TMP" server-config
rm -rf "\$TMP/server-config"
REMOTE

echo "[4/6] MySQL dump..."
ENV_FILE="$REPO_ROOT/backend/.env"
DB_DUMP_OK=0
if [[ -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  set -a
  source "$ENV_FILE"
  set +a
  if "${SSH[@]}" "mysqldump -h '$DB_HOST' -P '${DB_PORT:-3306}' -u '$DB_USER' -p'$DB_PASSWORD' '$DB_NAME' --single-transaction --routines --triggers 2>/dev/null | gzip -c > $REMOTE_TMP/mysql-${DB_NAME}.sql.gz"; then
    DB_DUMP_OK=1
  else
    echo "WARN: mysqldump selhal – použijte zálohu z panelu Webglobe."
  fi
else
  echo "WARN: backend/.env chybí – MySQL dump přeskočen."
fi

echo "[5/6] Git snapshot repozitáře..."
if git -C "$REPO_ROOT" rev-parse HEAD >/dev/null 2>&1; then
  REF="$(git -C "$REPO_ROOT" rev-parse HEAD)"
  git -C "$REPO_ROOT" archive --format=tar.gz -o "$DEST/repo-git-snapshot.tar.gz" HEAD
  echo "$REF" > "$DEST/repo-git-HEAD.txt"
fi

echo "[6/6] Stažení z VPS..."
for f in actors-all.tar.gz webapp-production.tar.gz webapp-staging.tar.gz server-config.tar.gz; do
  "${SCP[@]}" "$HOST:$REMOTE_TMP/$f" "$DEST/"
done
if [[ "$DB_DUMP_OK" -eq 1 ]]; then
  "${SCP[@]}" "$HOST:$REMOTE_TMP/mysql-${DB_NAME}.sql.gz" "$DEST/" 2>/dev/null || true
fi
"${SSH[@]}" "rm -rf $REMOTE_TMP" 2>/dev/null || true

mkdir -p "$DEST/local-secrets"
[[ -f "$ENV_FILE" ]] && cp "$ENV_FILE" "$DEST/local-secrets/backend.env" && chmod 600 "$DEST/local-secrets/backend.env"
[[ -f "$KEY" ]] && cp "$KEY" "$DEST/local-secrets/vps_ed25519" && chmod 600 "$DEST/local-secrets/vps_ed25519"

write_manifest() {
  {
    echo "{"
    echo "  \"created\": \"$(date -Iseconds)\","
    echo "  \"stamp\": \"$STAMP\","
    echo "  \"host\": \"$HOST\","
    echo "  \"db_dump\": $DB_DUMP_OK,"
    echo "  \"files\": ["
    local first=1
    for path in "$DEST"/*; do
      [[ -f "$path" ]] || continue
      local name size
      name="$(basename "$path")"
      size="$(stat -f%z "$path" 2>/dev/null || stat -c%s "$path")"
      [[ "$first" -eq 1 ]] && first=0 || echo ","
      printf '    {"name":"%s","bytes":%s}' "$name" "$size"
    done
    echo ""
    echo "  ]"
    echo "}"
  } > "$DEST/manifest.json"
}
write_manifest

ln -sfn "$DEST" "$BACKUP_ROOT/latest"

cat > "$DEST/RESTORE.md" <<'MD'
# Obnova po ztrátě serveru

1. **Kód:** GitHub clone nebo `repo-git-snapshot.tar.gz`
2. **DB:** `gunzip -c mysql-*.sql.gz | mysql -h HOST -u USER -p DBNAME`
3. **Actoři:** `sudo tar -xzf actors-all.tar.gz -C /opt` → v každém actoru `npm ci`
4. **Web:** `tar -xzf webapp-production.tar.gz -C /home/webmajak`
5. **Cron/nginx:** soubory z `server-config.tar.gz`
6. **Secrets:** `local-secrets/backend.env` → `backend/.env`

**Necommitujte** tuto složku na veřejný Git (hesla, DB dump).
MD

echo ""
echo "Hotovo: $DEST"
du -sh "$DEST"/* 2>/dev/null | sort -h
echo "Odkaz: $BACKUP_ROOT/latest"
