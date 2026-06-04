# Brána pohybu kamer – všechny prodejny (Windows)

Jeden balíček pro každou prodejnu. **IP NVR hledá sám** (`autodiscover_nvr: true`).

## Co jde automaticky / co ne

| Krok | Automaticky? |
|------|----------------|
| Najít NVR v lokální síti (`192.168.x.x`) | **Ano** – sken + rozlišení NVR vs. kamera |
| `prodejna_id` + `motion_secret` | **Ne** – jednou na prodejnu (jiné ID/secret) |
| Secret na produkční VPS (`CAMERA_MOTION_SECRETS`) | **Ne** – admin jednou přidá do `.env` |
| NVR: Detekce → **Upozornit iVMS** | **Ne** – jednou na místě v menu NVR |
| Instalace na PC | **Ne** – jednou na prodejnu (USB + instalátor) |

**Python na PC není potřeba** – instalátor stáhne portable Python (~25 MB, jednorázově, potřeba internetu).

Heslo NVR (`nvr_pass`) bývá **stejné** všude – pak stačí jedna šablona configu s jiným `prodejna_id`.

## Admin: přidání prodejny (produkce)

Soubor `/home/webmajak/secrets/camera_motion_secrets.json` + v `/home/webmajak/webapp/.env`:

```
CAMERA_MOTION_SECRETS_FILE=/home/webmajak/secrets/camera_motion_secrets.json
```

Restart: `systemctl restart webmajak`

Kompletní návod: **`INSTALL.md`**

`prodejna_id` = ID z MOBILMAJAK admin → Prodejny.

## Příprava USB (Mac)

```bash
cp -R scripts/camera-gateway /Volumes/USB/
# Volitelně hotový config pro danou prodejnu:
cp secrets/camera_motion_senimo.json /Volumes/USB/camera-gateway/config.json
# Upravte prodejna_id / motion_secret / nechte nvr_host prázdné
```

## Instalace na PC v prodejně

```powershell
cd C:\Temp\camera-gateway
Set-ExecutionPolicy -Scope Process Bypass
.\install-camera-gateway.ps1 -ProdejnaId 2 -ProdejnaNazev Senimo
```

Další prodejny – stejný postup, jiné `-ProdejnaId` / `-ProdejnaNazev`:

```powershell
.\install-camera-gateway.ps1 -ProdejnaId 3 -ProdejnaNazev Zlin
```

## config.json

```json
{
  "mobilmajak_api": "https://mobilmajak.com",
  "prodejna_id": 2,
  "motion_secret": "...",
  "autodiscover_nvr": true,
  "nvr_host": "",
  "nvr_user": "admin",
  "nvr_pass": "..."
}
```

`nvr_host` prázdné = při startu sken sítě. Pokud autodetekce na dané prodejně selže, doplňte IP ručně (jako Senimo `192.168.1.104`).

## Test ručně

```powershell
cd C:\ProgramData\Mobilmajak\CameraGateway-Senimo
.\python-embed\python.exe camera_motion_gateway.py --config config.json --discover-nvr
.\python-embed\python.exe camera_motion_gateway.py --config config.json --test-isapi
```

## Senimo

Složka `scripts/senimo-gateway/` je alias se stejným obsahem – pro nové prodejny používejte **`camera-gateway`**.
