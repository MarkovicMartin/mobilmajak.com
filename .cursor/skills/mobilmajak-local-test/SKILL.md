---
name: mobilmajak-local-test
description: Spustí plný lokální test MOBILMAJAK (production frontend build, Django API, MySQL přes backend/.env, prohlížeč). Použij při žádosti o testovací relaci, lokální build, lokální test, otestovat na localhost, spustit aplikaci lokálně, nebo ověřit frontend po změnách bez deploye.
---

# MOBILMAJAK – lokální testovací relace

## Bez potvrzení (povinné pro agenta)

Uživatel žádá-li **testovací relaci**, **lokální build** nebo **spustit lokálně**:

1. **Okamžitě spusť** `.\scripts\run-local.ps1` (nebo `-Rebuild` po změnách ve frontendu) – **neptej se** „mohu spustit“, „chcete potvrdit“ ani podobně.
2. Použij Shell tool s **`block_until_ms: 0`** (dlouho běžící proces na pozadí), pak sleduj terminál (`OK Backend běží`, `OK Frontend běží` nebo chybu).
3. Nepoužívej `AskQuestion` ani čekej na schválení – příkaz je v **allowlistu** (`.cursor/hooks/shell-policy.ps1`, pravidlo `agent-automation.mdc`).
4. **Neprovádět** jako náhradu: samotné `serve` s proxy na produkci, pokud uživatel nechce výslovně jen UI bez DB.

## Jeden příkaz

Z kořene repozitáře (PowerShell):

```powershell
.\scripts\run-local.ps1
```

Po změnách ve frontendu (servis, analytics, profil, …):

```powershell
.\scripts\run-local.ps1 -Rebuild
```

## Co skript dělá

| Krok | Výsledek |
|------|----------|
| `backend/.env` | Z `.env.example` pokud chybí; heslo z `DB_PASSWORD` v souboru **nebo** proměnné prostředí `$env:DB_PASSWORD` |
| Python venv + `pip install` | Django na `127.0.0.1:8000` |
| `npm run build` (pokud chybí build / `-Rebuild`) | Statický build |
| `npm run serve:build` | UI na `http://localhost:8001`, `/api` → lokální Django |
| Prohlížeč | Otevře `http://localhost:8001` |

## Předpoklady a chyby

- **`DB_PASSWORD`**: v `backend/.env` **nebo** před spuštěním `$env:DB_PASSWORD = '...'` (skript doplní do `.env`). Nikdy necommitovat `.env`.
- Chybí heslo → skript skončí s jasnou chybou; uživateli napiš jednu větu co doplnit, **bez** opakovaného ptání na potvrzení spuštění.
- Porty **8000** a **8001** – skript je před startem uvolní.
- Ukončení: **Ctrl+C** v terminálu se skriptem.

## Po spuštění agenta

1. Ověř v logu `OK Backend running` a `OK Frontend running`.
2. Volitelně: `Invoke-WebRequest http://127.0.0.1:8000/health/` a `http://localhost:8001/` (ne `curl` kvůli hookům – nebo příkaz je v rámci skriptu).
3. Uživateli sděl URL: **http://localhost:8001** a že API běží přes lokální Django + MySQL.

## Rychlá vs. plná relace

| Potřeba | Příkaz |
|---------|--------|
| Plný test (DB + login + build) | `.\scripts\run-local.ps1` |
| Čerstvý frontend build | `.\scripts\run-local.ps1 -Rebuild` |
| Jen UI bez DB (výjimka) | `cd frontend; $env:API_PROXY='https://mobilmajak.com'; npm run serve:build` |

Výchozí pro „testovací relaci“ je vždy **`run-local.ps1`**.

## Související soubory

- `scripts/run-local.ps1` – hlavní orchestrátor
- `scripts/run-local.cmd` – zástupce pro dvojklik
- `frontend/scripts/serve-build.js` – build server + proxy (`API_PROXY`)
