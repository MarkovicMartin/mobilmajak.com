# Záloha projektu a serveru (disaster recovery)

## Co kam patří

| Část | Kde je „pravda“ | Záloha |
|------|-----------------|--------|
| Zdrojový kód | **GitHub** (`mobilmajak.com`) | `git push` po každé větší změně |
| Actoři Symplio/Zásilkovna | **VPS** `/opt/actor/` | `backup-full-server.sh` → `actors-all.tar.gz` |
| Produkce + staging | **VPS** `/home/webmajak/` | stejný skript → `webapp-*.tar.gz` |
| MySQL | **Webglobe** `db.dw300.webglobe.com` | `mysql-*.sql.gz` ve skriptu + panel Webglobe |
| Cron, nginx | **VPS** | `server-config.tar.gz` |
| Hesla, SSH | **Lokálně** `backend/.env`, `.ssh/` | `local-secrets/` ve složce zálohy |

## Kompletní lokální záloha (doporučeno 1× týdně + před velkými změnami)

```bash
chmod +x scripts/backup-full-server.sh scripts/backup-init-offsite-git.sh scripts/backup-sync-manifests-to-git.sh
./scripts/backup-full-server.sh
```

Výstup (mimo git repozitář projektu):

```text
../mobilmajak-backups/
  20260604-210000/
    actors-all.tar.gz
    webapp-production.tar.gz
    webapp-staging.tar.gz
    server-config.tar.gz
    mysql-multi_724223.sql.gz
    repo-git-snapshot.tar.gz
    local-secrets/          # .env + SSH klíč
    manifest.json
    RESTORE.md
  latest → symlink na poslední zálohu
```

Větší archivy (s `node_modules`): `./scripts/backup-full-server.sh --with-node-modules`

## Git – co dává smysl

- **Hlavní repo** – kód aplikace (už máte). Actoři jsou v `.gitignore` (`actors_backup/`).
- **Privátní repo záloh** – jen manifesty, ne dumpy:

```bash
./scripts/backup-init-offsite-git.sh git@github.com:VASE-UCET/mobilmajak-backups.git
./scripts/backup-full-server.sh
./scripts/backup-sync-manifests-to-git.sh
git -C ../mobilmajak-backups push
```

**Nikdy** necommitujte na veřejný Git: `mysql-*.sql.gz`, `local-secrets/`, SSH klíče.

## Jen jeden actor (rychlé)

```powershell
.\scripts\backup-actor-vps.ps1
```

## Obnova po smazání VPS

Viz `RESTORE.md` v konkrétní složce zálohy – stručně: nový VPS, obnova tarů, import MySQL, obnova crontab, `npm ci` v actorech.

## Automatizace (volitelně)

Na Macu `launchd` nebo cron:

```cron
0 3 * * 0 cd /cesta/k/mobilmajak.com && ./scripts/backup-full-server.sh
```

Windows: Plánovač úloh → `backup-full-server.ps1`.
