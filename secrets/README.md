# Lokální tajné soubory (gitignore – na GitHub se neposílají)

| Soubor | Účel |
|--------|------|
| `secrets/mobilmajak_vps_ed25519` nebo `secrets/mobilmajak_vps_ed25519.USER_INPUT_REQ` | Privátní SSH klíč (celý blok `-----BEGIN … KEY-----` … `-----END …`) |
| `backend/.env` | DB heslo – šablona `backend/.env.example` |
| `frontend/.env.production` | `REACT_APP_CLARITY_PROJECT_ID` – šablona `frontend/.env.example` |
| `secrets/actor-cesta-na-vps.USER_INPUT_REQ` | Cesta k actoru na VPS po `grep techniciMap` |

**Privátní klíč (funguje):** `.ssh/webmajak_vps/mobilmajak_vps_ed25519` v kořeni projektu (v gitignore)

SSH z PC:
```powershell
ssh -i ".ssh\webmajak_vps\mobilmajak_vps_ed25519" root@194.182.87.138
```
Po `icacls` musí mít soubor jen váš účet `(F)` – jinak OpenSSH hlásí „bad permissions“.

**Staging deploy (Mac/Linux):**
```bash
chmod +x scripts/deploy-staging.sh scripts/grant-staging-tickets-admin.sh
./scripts/deploy-staging.sh
```

**Správa ticketů pro uživatele (např. markovic) – spusťte až PO připojení SSH (ne v jednom řádku s `ssh`):**
```bash
./scripts/grant-staging-tickets-admin.sh markovic
```
Nebo na serveru:
```bash
sudo -u webmajak bash -lc 'cd /home/webmajak/staging && source venv/bin/activate && export DJANGO_SETTINGS_MODULE=webapp.settings_production && python manage.py grant_tickets_admin markovic'
```
Po změně modulů: **odhlásit a znovu přihlásit** v prohlížeči.

**Cron – plány na staging (jednorázová instalace):**

```bash
./scripts/install-staging-plans-cron.sh
```

Nastaví u uživatele `webmajak`: 1. den v měsíci 6:00 `ensure_monthly_plans --rust 10`, denně 7:00 `prepocet_plan_prodejci`. Logy: `staging/logs/`.

**Produkce** – stejné příkazy, cesta např. `/home/webmajak/app`. Ručně: `ensure_monthly_plans --mesic 2026-07`, `prepocet_plan_prodejci --rok 2026`, od 15. v měsíci `--force` pro aktuální měsíc.

Po „Založit plány na rok“ z UI se prodejci přepočítají hned; denní cron od 15. doplňuje směny.

**Pilot pohybu kamer (bez obrazu na serveru):**

| Soubor | Účel |
|--------|------|
| `secrets/camera_motion_secrets.json` | `{"ID_PRODEJNY":"hex_secret"}` – jeden secret na pilotní prodejnu |

Na VPS v `backend/.env` (nebo systemd): `CAMERA_MOTION_SECRETS_FILE=/home/webmajak/secrets/camera_motion_secrets.json`

Brána na PC v LAN: `scripts/camera_motion_gateway.py` (čte ISAPI alertStream z NVR, posílá jen `motion: true/false`).

**Kompletní záloha serveru + actoři (lokálně, mimo git projektu):**

```bash
./scripts/backup-full-server.sh
```

Výstup: `../mobilmajak-backups/`. Návod a obnova: [`docs/zaloha-disaster-recovery.md`](../docs/zaloha-disaster-recovery.md). Privátní git jen pro manifesty: `backup-init-offsite-git.sh` + `backup-sync-manifests-to-git.sh`.
