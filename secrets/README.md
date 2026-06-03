# Lokální tajné soubory (gitignore – na GitHub se neposílají)

| Soubor | Účel |
|--------|------|
| `secrets/mobilmajak_vps_ed25519` nebo `secrets/mobilmajak_vps_ed25519.USER_INPUT_REQ` | Privátní SSH klíč (celý blok `-----BEGIN … KEY-----` … `-----END …`) |
| `backend/.env` | DB heslo – šablona `backend/.env.example` |
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
