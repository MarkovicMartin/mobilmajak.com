# Lokální tajné soubory (`secrets/` – celá složka v gitignore)

Šablony bez hesel: [`config/secrets-examples/`](../config/secrets-examples/).

| Soubor | Účel |
|--------|------|
| `secrets/mobilmajak_vps_ed25519` nebo `secrets/mobilmajak_vps_ed25519.USER_INPUT_REQ` | Privátní SSH klíč (celý blok `-----BEGIN … KEY-----` … `-----END …`) |
| `backend/.env` | DB heslo – šablona `backend/.env.example` |
| `frontend/.env.production` | `REACT_APP_CLARITY_PROJECT_ID` – šablona `frontend/.env.example` |
| `secrets/mobilmajak-finance.json` | Finance modul – šablona `config/secrets-examples/mobilmajak-finance.example.json` |
| `secrets/mobilmajak-slack.json` | Slack bot token + signing secret – šablona `config/secrets-examples/mobilmajak-slack.example.json` |
| `secrets/mobilmajak-symplio.json` | Symplio actor login – šablona `config/secrets-examples/mobilmajak-symplio.example.json` |
| `secrets/slacktoken.json` | **legacy** – starý formát; stále funguje jako záloha, raději migruj na `mobilmajak-slack.json` |

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

**Slack (úkoly – notifikace + `/ukol` wizard):**

Kompletní návod pro Slack portal: **[docs/slack-app-produkce.md](../docs/slack-app-produkce.md)**

**Doporučený soubor** (jako u financí):

```bash
cp config/secrets-examples/mobilmajak-slack.example.json secrets/mobilmajak-slack.json
# vyplnit bot_token + signing_secret
```

V `backend/.env` (lokálně i na VPS):

```
SLACK_SECRETS_FILE=../secrets/mobilmajak-slack.json
```

Backend načte z JSON; **env proměnné** (`SLACK_BOT_TOKEN`, `SLACK_SIGNING_SECRET`, …) mají **přednost** před souborem.

**Signing secret** → Slack app → Basic Information → App Credentials → Signing Secret.

**Bot token** (`xoxb-...`) → Install App → Bot User OAuth Token.

**Migrace ze `secrets/slacktoken.json`:** zkopíruj token do `bot_token`, signing secret doplň do `signing_secret`, `app_url` nech `https://mobilmajak.com`.

Na **produkčním VPS** buď:
- nahraj `secrets/mobilmajak-slack.json` a nastav `SLACK_SECRETS_FILE`, **nebo**
- nech hodnoty přímo v `/home/webmajak/app/backend/.env` (deploy `.env` nepřepisuje).

Po změně: `sudo systemctl restart gunicorn`.

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
| `secrets/mobilmajak-finance.json` | Finance modul – Fio token, Packeta admin loginy per prodejna, Google Sheets náklady. Šablona: `config/secrets-examples/mobilmajak-finance.example.json`. V `backend/.env`: `FINANCE_SECRETS_FILE=../secrets/mobilmajak-finance.json`, `FINANCE_FIO_ENABLED=0` (Fio až po admin účtu) |
| `secrets/google-sheets-service-account.json` | Service account pro import tabulky nákladů |
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

**Windows instalátor (Globus, ID 1):** `secrets/camera_motion_globus.json`; složky `scripts/camera-gateway/` + `scripts/globus-gateway/` na USB, `install-globus-camera-gateway.cmd` jako správce. Checklist: `scripts/globus-gateway/README.md`.

**Windows instalátor (Čepkov / Zlín, ID 3):** `scripts/zlin-gateway/config.example.json` → `secrets/camera_motion_zlin.json`; složky `scripts/camera-gateway/` + `scripts/zlin-gateway/` na USB, `install-zlin-camera-gateway.cmd` jako správce. Checklist: `scripts/zlin-gateway/README.md`.

**Windows instalátor (Šternberk, ID 6):** `scripts/sternberk-gateway/config.example.json` → `secrets/camera_motion_sternberk.json`; složky `scripts/camera-gateway/` + `scripts/sternberk-gateway/` na USB, `install-sternberk-camera-gateway.cmd` jako správce. Checklist: `scripts/sternberk-gateway/README.md`.

**Windows instalátor (Přerov, ID 4):** `scripts/prerov-gateway/config.example.json` → `secrets/camera_motion_prerov.json`; složky `scripts/camera-gateway/` + `scripts/prerov-gateway/` na USB, `install-prerov-camera-gateway.cmd` jako správce. Checklist: `scripts/prerov-gateway/README.md`.

**Windows instalátor (Vsetín, ID 5):** `secrets/camera_motion_vsetin.json`; složky `scripts/camera-gateway/` + `scripts/vsetin-gateway/` na USB, `install-vsetin-camera-gateway.cmd` jako správce. Checklist: `scripts/vsetin-gateway/README.md`.

**Kompletní záloha serveru + actoři (lokálně, mimo git projektu):**

```bash
./scripts/backup-full-server.sh
```

Výstup: `../mobilmajak-backups/`. Návod a obnova: [`docs/zaloha-disaster-recovery.md`](zaloha-disaster-recovery.md). Privátní git jen pro manifesty: `backup-init-offsite-git.sh` + `backup-sync-manifests-to-git.sh`.

**Symplio actory (VPS):**

- Sdílený login: `/opt/scripts/symplio-shared/` (`symplio-credentials.js`, `symplio-login.js`)
- Deploy: `./scripts/symplio-shared/deploy.sh`
- Env ve wrapperech: `SYMPLIO_SECRETS_FILE` + `SYMPLIO_SCRIPTS_DIR=/opt/scripts/symplio-shared`
- Actory: prodeje `/opt/actor/ACTOR_FINALL_WEB_PRODEJE_ALL/`, výkupy `/opt/actor/ACTOR_VYKUPY/`, pokladna `/opt/scripts/symplio-pokladna-historie/`
- Credentials: `secrets/mobilmajak-symplio.json` → na VPS `/home/webmajak/secrets/mobilmajak-symplio.json`
- **Rotace hesla (S5):** změnit jen jeden JSON (`mobilmajak-symplio.json`) – všechny actory načítají stejný soubor přes `SYMPLIO_SECRETS_FILE`. Po změně hesla není potřeba upravovat jednotlivé actory.
