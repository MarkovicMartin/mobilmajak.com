# Brána pohybu kamer – instalace (produkce)

> **Výchozí API:** `https://mobilmajak.com` (ne staging).  
> Staging (`https://staging.mobilmajak.com`) jen pro vývoj před deployem.

## Před návštěvou prodejny (admin na Macu)

### 1. Secret na VPS (produkce)

Soubor `/home/webmajak/secrets/camera_motion_secrets.json`:

```json
{"2":"hex_secret_senimo","3":"hex_secret_zlin"}
```

Stejná hodnota secretu může být pro všechny prodejny; **ID musí být unikátní** (`prodejna_id` z MOBILMAJAK).

V `/home/webmajak/webapp/.env`:

```
CAMERA_MOTION_SECRETS_FILE=/home/webmajak/secrets/camera_motion_secrets.json
```

Restart: `systemctl restart webmajak`

### 2. USB balíček

```bash
cp -R scripts/camera-gateway /Volumes/USB/
```

Pro každou prodejnu připravte `config.json` (necommitovat):

```json
{
  "mobilmajak_api": "https://mobilmajak.com",
  "prodejna_id": 2,
  "motion_secret": "stejny_hex_jako_v_secrets_json",
  "autodiscover_nvr": true,
  "nvr_host": "",
  "nvr_user": "admin",
  "nvr_pass": "heslo_NVR_na_miste"
}
```

Šablona: `config.example.json`

### 3. NVR (jednou na místě)

Detekce pohybu → Propojení → **Upozornit iVMS** u kanálu.

## Instalace na PC v prodejně (Windows)

PowerShell **jako správce**:

```cmd
cd C:\Temp\camera-gateway
install-camera-gateway.cmd
```

Nebo:

```powershell
powershell -ExecutionPolicy Bypass -File .\install-camera-gateway.ps1 -ProdejnaId 2 -ProdejnaNazev Senimo
```

Aktualizace bez přepsání `config.json`:

```cmd
update-installed-gateway.cmd
```

## Senimo

Složka `scripts/senimo-gateway/` – stejná logika, pevné ID 2. Pro nové prodejny preferujte `camera-gateway/`.

## Přepnutí ze staging na produkci (už nainstalované PC)

Upravit `C:\ProgramData\Mobilmajak\SenimoCameraGateway\config.json` (nebo `CameraGateway-*`):

```json
"mobilmajak_api": "https://mobilmajak.com"
```

Pak:

```powershell
Stop-ScheduledTask -TaskName 'Mobilmajak-Senimo-CameraGateway' -ErrorAction SilentlyContinue
Start-ScheduledTask -TaskName 'Mobilmajak-Senimo-CameraGateway'
```

## Ověření

- Log: `C:\ProgramData\Mobilmajak\...\gateway.log` – `stale nasloucham`, `gateway` události
- MOBILMAJAK → Směny → Není v práci → stav kamery u prodejny

## Konvence pro nové instalační soubory

| Položka | Hodnota |
|---------|---------|
| `mobilmajak_api` | `https://mobilmajak.com` |
| PowerShell skripty | ASCII only (bez českých znaků) |
| Spuštění `.ps1` | `.cmd` wrapper nebo `-ExecutionPolicy Bypass` |
| Úlohy Plánovače | hlavní + `-WakeKick`, start +30 s |
| Dokumentace | tento soubor + `README.md` v balíčku |
