# Lokální tajné soubory (gitignore – na GitHub se neposílají)

| Soubor | Účel |
|--------|------|
| `secrets/napojeno_ed25519` nebo `secrets/napojeno_ed25519.USER_INPUT_REQ` | Privátní SSH klíč (celý blok `-----BEGIN … KEY-----` … `-----END …`) |
| `backend/.env` | DB heslo – šablona `backend/.env.example` |
| `secrets/actor-cesta-na-vps.USER_INPUT_REQ` | Cesta k actoru na VPS po `grep techniciMap` |

**Privátní klíč (funguje):** `.ssh/webmajak_vps/napojeno_ed25519` v kořeni projektu (v gitignore)

SSH z PC:
```powershell
ssh -i ".ssh\webmajak_vps\napojeno_ed25519" root@194.182.87.138
```
Po `icacls` musí mít soubor jen váš účet `(F)` – jinak OpenSSH hlásí „bad permissions“.
