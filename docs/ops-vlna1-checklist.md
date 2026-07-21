# Ops checklist – Vlna 1 (F1 Finance, Přístupy, R11) + Symplio deploy

Tyto kroky **neběží automaticky z agenta** – spusť na VPS / lokálně s potvrzením.

## Symplio S1–S4 (deploy shared)

```bash
./scripts/symplio-shared/deploy.sh
```

Ruční ověření na VPS (login OK bez lokálních credentials kopií):

- Prodeje: actor `/opt/actor/ACTOR_FINALL_WEB_PRODEJE_ALL` (cron `/opt/run-prodeje-actor-safe.sh`)
- Výkupy: `/opt/actor/ACTOR_VYKUPY`
- Výdejky: `/opt/run-sklad-vydejky-actor-safe.sh` (nebo wrapper v actor dir)
- Pokladna: `/opt/scripts/run-symplio-pokladna-safe.sh`

Očekávané env: `SYMPLIO_SECRETS_FILE=/home/webmajak/secrets/mobilmajak-symplio.json`,  
`SYMPLIO_SCRIPTS_DIR=/opt/scripts/symplio-shared`.

Rotace hesla: jeden JSON – viz [secrets-setup.md](secrets-setup.md).

---

## F1 – Finance (produkce)

1. Secrets (až bude token): `secrets/mobilmajak-finance.json` → VPS (viz secrets-setup).
2. V produkčním `backend/.env` / webapp env:
   - `FINANCE_MODULE_ENABLED=1`
   - `FINANCE_FIO_ENABLED=1` **až po** Fio tokenu v secrets (bez tokenu nechat `0`)
3. Cron:

```bash
./scripts/install-finance-cron.sh
```

4. Smoke:

```bash
# na VPS jako webmajak ve webapp
python manage.py import_fio_naklady --days 3
```

Pak v UI: Finance → „K zařazení“. Bez Fio tokenu ověř jen modul s `FINANCE_FIO_ENABLED=0`.

---

## Přístupy P1 + Mastersheet

Lokálně / na VPS (venv):

```bash
./scripts/backend-run.sh manage.py migrate_company_access --dry-run
# pokud dry-run OK a chceš zápis:
./scripts/backend-run.sh manage.py migrate_company_access

./scripts/backend-run.sh manage.py audit_mastersheet_logins --import-missing --dry-run
./scripts/backend-run.sh manage.py audit_mastersheet_logins --import-missing
./scripts/backend-run.sh manage.py audit_mastersheet_logins --fill-urls --dry-run
./scripts/backend-run.sh manage.py audit_mastersheet_logins --fill-urls
```

Ruční vzorek: 1–2 prodejny v UI Přístupy.

---

## R11 – Reklamace reminders (produkce, do 31. 8.)

**Bez** `STAGING=1`:

```bash
./scripts/install-reklamace-reminders-cron.sh
```

Smoke:

```bash
# na VPS webapp
python manage.py check_reklamace_reminders --dry-run
```

Ověřit in-app + Slack ID; cron 07:15.

---

## Objednávky O3 – SLA cron (po deployi backendu)

```bash
./scripts/install-orders-sla-cron.sh
# dry-run:
./scripts/backend-run.sh manage.py check_orders_sla_reminders --dry-run
```

Env: `ORDERS_SLA_DAYS=7` (default). Cron **nikdy** nemění status – jen Slack.
