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

**Slack notifikace úkolů (volitelné):**

V `backend/.env` na stagingu / produkci:

```
SLACK_BOT_TOKEN=xoxb-...
MOBILMAJAK_APP_URL=https://staging.mobilmajak.com
```

Volitelně kanálový webhook (fallback bez bota):

```
SLACK_TASKS_WEBHOOK_URL=https://hooks.slack.com/services/...
```

### Slack app – nastavení bota pro DM

1. Na [api.slack.com/apps](https://api.slack.com/apps) vytvořte **From scratch** appku (workspace MOBILMAJAK).
2. **OAuth & Permissions** → Bot Token Scopes:
   - `chat:write` – odesílání DM
   - `users:read.email` – vyhledání uživatele podle e-mailu
3. **Install App** do workspace → zkopírujte **Bot User OAuth Token** (`xoxb-...`) do `SLACK_BOT_TOKEN`.
4. V **Manage Distribution** / nastavení appky povolte instalaci do workspace (pokud je appka jen pro jeden workspace, stačí Install).
5. Uživatelé musí mít v MOBILMAJAK vyplněný **e-mail shodný se Slack účtem** (lookup přes `users.lookupByEmail`).
6. Bota není nutné přidávat do kanálů pro DM – DM jdou přímo na uživatele.

Test lookupu (na serveru s tokenem v env):

```bash
curl -s -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  "https://slack.com/api/users.lookupByEmail?email=vas@email.cz"
```

Cron (např. každou hodinu u uživatele `webmajak`):

```bash
0 * * * * cd /home/webmajak/staging/backend && source ../venv/bin/activate && export DJANGO_SETTINGS_MODULE=webapp.settings_production && python manage.py notify_task_deadlines >> ../logs/task-slack-notify.log 2>&1
```

Test bez odeslání: `python manage.py notify_task_deadlines --dry-run`

Bez `SLACK_BOT_TOKEN` (a bez webhooku) příkaz jen vypíše úkoly a nic neodešle.

**Události s DM:** nové přiřazení, blížící se termín, po termínu, čeká schválení, dokončení, potvrzení zadavateli při založení.

**Pilot pohybu kamer (bez obrazu na serveru):**

| Soubor | Účel |
|--------|------|
| `secrets/mobilmajak-finance.json` | Finance modul – Fio token, Packeta admin loginy per prodejna, Google Sheets náklady. Šablona: `mobilmajak-finance.example.json` |
| `secrets/google-sheets-service-account.json` | Service account pro import tabulky nákladů. Šablona: `google-sheets-service-account.example.json` |
| `secrets/camera_motion_secrets.json` | `{"ID_PRODEJNY":"hex_secret"}` – jeden secret na pilotní prodejnu |

Na produkčním VPS v `/home/webmajak/webapp/.env`:

```
CAMERA_MOTION_SECRETS_FILE=/home/webmajak/secrets/camera_motion_secrets.json
```

Restart: `systemctl restart webmajak`

V `config.json` na PC / v `secrets/camera_motion_*.json`: **`mobilmajak_api": "https://mobilmajak.com"`**

Návod k instalaci: `scripts/camera-gateway/INSTALL.md`

**Bez PC na prodejně (volitelné):** NVR pošle HTTP alarm na produkci.

```bash
python3 scripts/camera_motion_setup_nvr_http.py --config secrets/camera_motion_senimo.json --show-url
python3 scripts/camera_motion_setup_nvr_http.py --config secrets/camera_motion_senimo.json
```

Ručně v NVR: **Configuration → Network → Advanced → HTTP(S) alarm** (nebo Event → HTTP notifikace) – vložte webhook URL ze skriptu, typ události **VMD**.

**S bránou na PC:** `scripts/camera_motion_gateway.py` (záloha, pokud HTTP z NVR nejde).

**Windows instalátor (Senimo):** složka `scripts/senimo-gateway/` – zkopírovat na USB, `config.json` z `camera_motion_senimo.json`, spustit `install-senimo-camera-gateway.ps1` jako správce.

**Windows instalátor (Globus, ID 1):** šablona `secrets/camera_motion_globus.example.json` → `camera_motion_globus.json`; složky `scripts/camera-gateway/` + `scripts/globus-gateway/` na USB, `install-globus-camera-gateway.cmd` jako správce. Checklist: `scripts/globus-gateway/README.md`.

**Windows instalátor (Čepkov / Zlín, ID 3):** `scripts/zlin-gateway/config.example.json` → `secrets/camera_motion_zlin.json`; složky `scripts/camera-gateway/` + `scripts/zlin-gateway/` na USB, `install-zlin-camera-gateway.cmd` jako správce. Checklist: `scripts/zlin-gateway/README.md`.

**Windows instalátor (Šternberk, ID 6):** `scripts/sternberk-gateway/config.example.json` → `secrets/camera_motion_sternberk.json`; složky `scripts/camera-gateway/` + `scripts/sternberk-gateway/` na USB, `install-sternberk-camera-gateway.cmd` jako správce. Checklist: `scripts/sternberk-gateway/README.md`.

**Windows instalátor (Přerov, ID 4):** `scripts/prerov-gateway/config.example.json` → `secrets/camera_motion_prerov.json`; složky `scripts/camera-gateway/` + `scripts/prerov-gateway/` na USB, `install-prerov-camera-gateway.cmd` jako správce. Checklist: `scripts/prerov-gateway/README.md`.

**Kompletní záloha serveru + actoři (lokálně, mimo git projektu):**

```bash
./scripts/backup-full-server.sh
```

Výstup: `../mobilmajak-backups/`. Návod a obnova: [`docs/zaloha-disaster-recovery.md`](../docs/zaloha-disaster-recovery.md). Privátní git jen pro manifesty: `backup-init-offsite-git.sh` + `backup-sync-manifests-to-git.sh`.
