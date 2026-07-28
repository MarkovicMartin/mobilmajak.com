# Skripty MOBILMAJAK

Přehled – co je provozní, co plánované rozšíření. Nepřidávejte jednorázové kopie deploy/cron; rozšiřte existující skript.

## Deploy a staging

| Skript | Účel |
|--------|------|
| `deploy-staging.sh` | Staging deploy + smoke (krok 1); po deployi staging běží default 2h |
| `deploy-staging.ps1` | Totéž pro Windows |
| `staging-app.sh` | Zapnout/vypnout/prodloužit staging workery na VPS (`start\|stop\|extend\|status`) |
| `staging-app-control.sh` | Stejné ovládání přímo na VPS (`/opt/scripts/…`) |
| `frontend-build-vps.sh` | `npm ci` + aktualizace browserslist + build (volá deploy) |
| `post-deploy-smoke.sh` | Health + `manage.py check` + shifts import (volá deploy) |
| `local-predeploy-check.sh` | Lokální `manage.py check` přes `backend/.venv` |
| `backend-run.sh` | Libovolný příkaz v `backend/.venv` (check, test, …) |
| `setup-backend-venv.sh` | Vytvoření/obnova `backend/.venv` (Python 3.12+) |
| `staging-post-deploy.sh` | Migrace, collectstatic, restart (volá deploy) |
| `deploy-production.sh` / `.ps1` | Produkce (až po OK stagingu) |
| `production-post-deploy.sh` | Post-deploy produkce |
| `merge-to-production.sh` | Merge větev → produkce |
| `grant-staging-tickets-admin.sh` | Oprávnění ticketů na staging |

## Plány a Slack notifikace (cron na VPS)

| Skript | Účel |
|--------|------|
| `install-staging-plans-cron.sh` | Deprecated – plány na staging; použij `install-production-plans-cron.sh` |
| `install-production-plans-cron.sh` | Cron `ensure_monthly_plans` + `prepocet_plan_prodejci` na produkci (`webmajak`) |
| `install-task-slack-notify-cron.sh` | Cron `notify_shift_task_recap` (*/5) + `notify_task_deadlines` (hourly); `STAGING=1` pro staging |
| `install-daily-report-cron.sh` | Cron denního Slack reportu |
| `install-orders-sla-cron.sh` | Cron SLA připomínek objednávek |
| `install-reklamace-reminders-cron.sh` | Cron připomínek reklamací |

Detaily a ruční řádky crontab: [`docs/secrets-setup.md`](../docs/secrets-setup.md).

## Záloha (off-site, mimo git projektu)

| Skript | Účel |
|--------|------|
| `backup-full-server.sh` / `.ps1` | Kompletní záloha VPS → `../mobilmajak-backups/` |
| `backup-init-offsite-git.sh` | Privátní git jen pro manifesty záloh |
| `backup-sync-manifests-to-git.sh` | Sync manifestů po záloze |
| `backup-actor-vps.ps1` | Záloha actor složky na VPS |

Návod: [`docs/zaloha-disaster-recovery.md`](../docs/zaloha-disaster-recovery.md).

## Kamery – pilot pohybu (bez obrazu na serveru)

| Soubor | Účel |
|--------|------|
| `camera_motion_gateway.py` | Brána v LAN: NVR alertStream → API `motion: true/false` |
| `camera_motion_test_globus.sh` | Test pilotu Globus (lokálně) |
| `camera_motion_test_zlin.sh` | Test pilotu Čepkov / Zlín (lokálně) |
| `camera_motion_test_sternberk.sh` | Test pilotu Šternberk (lokálně) |
| `camera_motion_test_vsetin.sh` | Test pilotu Vsetín (lokálně) |
| `globus-gateway/` | Instalátor Windows pro Globus (ID 1) + README checklist |
| `zlin-gateway/` | Instalátor Windows pro Čepkov / Zlín (ID 3) + README checklist |
| `sternberk-gateway/` | Instalátor Windows pro Šternberk (ID 6) + README checklist |
| `vsetin-gateway/` | Instalátor Windows pro Vsetín (ID 5) + README checklist |
| `camera_motion_gateway.example.json` | Příklad konfigurace |

Tajemství: `secrets/camera_motion_secrets.json` – viz `docs/secrets-setup.md`.

## Lokální vývoj

| Skript | Účel |
|--------|------|
| `run-local.cmd` / `run-local.ps1` / `run-local.sh` | Plná lokální relace (skill mobilmajak-local-test) |
| `setup-backend-venv.sh` | Python 3.12+ venv v `backend/.venv` |
| `backend-run.sh` | Django příkazy v venv: `./scripts/backend-run.sh manage.py check` |

## Symplio / integrace (samostatná oblast)

| Složka | Účel |
|--------|------|
| `symplio-backfill-pre2024/` | Doplňování starších měsíců Symplio |

## Ostatní

| Skript | Účel |
|--------|------|
| `git-switch-branch.sh` | Přepnutí větve na VPS |
| `setup-git-repo.sh` | Počáteční git na serveru |
| `check-technik-map.js` | Kontrola mapy techniků |
| `compare-symplio-month.ps1` | Porovnání měsíce Symplio |

Backend-only pomocné skripty: `backend/scripts/` (cron dedupe, migrace).
