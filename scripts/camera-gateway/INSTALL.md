# Brána pohybu kamer – jeden postup pro všechny prodejny

> **API:** vždy `https://mobilmajak.com`  
> **Sdílený kód:** `scripts/camera-gateway/` (instalátor, úlohy Plánovače, auto-start)  
> **Per prodejna:** jen IP + `prodejna_id` v `prodejny.json`

## 1. Mac – příprava (vždy stejné kroky)

### a) Upravit `scripts/camera-gateway/prodejny.json`

Přidat/upravit blok prodejny (příklad Šternberk):

```json
"sternberk": {
  "prodejna_id": 6,
  "prodejna_nazev": "Sternberk",
  "nvr_host": "10.0.1.112",
  "camera_host": "192.168.254.6",
  "install_cmd": "install-sternberk-camera-gateway.cmd",
  "gateway_dir": "sternberk-gateway"
}
```

`prodejna_id` ověř v adminu Prodejny (nebo `manage.py shell` na VPS).

### b) Vygenerovat config + secrets

```bash
chmod +x scripts/prepare-camera-gateway.sh
./scripts/prepare-camera-gateway.sh sternberk              # jen soubory
./scripts/prepare-camera-gateway.sh sternberk /Volumes/USB # + zkopírovat na USB
```

Vytvoří:
- `secrets/camera_motion_<slug>.json`
- `scripts/<gateway_dir>/config.json` (vždy s `prodejna_nazev`)

### c) Secret na VPS

```bash
openssl rand -hex 32
```

Do `/home/webmajak/secrets/camera_motion_secrets.json` přidat `"<prodejna_id>": "<hex>"`,  
stejný hex do `motion_secret` v lokálním configu, pak:

```bash
systemctl restart webmajak
```

### d) USB obsah

```
USB/
  camera-gateway/          ← vždy
  sternberk-gateway/     ← config.json uvnitř
    install-*-camera-gateway.cmd
```

## 2. NVR (jednou na místě)

**Detekce pohybu → Propojení → Upozornit iVMS** u kanálu kamery.

## 3. PC v prodejně (Windows, správce)

```cmd
cd C:\Temp\sternberk-gateway
install-sternberk-camera-gateway.cmd
```

V PowerShellu musí být `.\install-sternberk-camera-gateway.cmd`.

Instalátor:
1. Nainstaluje Python do `C:\ProgramData\Mobilmajak\CameraGateway-<Nazev>\`
2. Zaregistruje úlohy Plánovače (viz níže)
3. Otestuje ISAPI + motion POST

## 4. Auto-start po vypnutí / spánku (všechny prodejny)

Stejný mechanismus v `register-gateway-tasks.ps1`:

| Úloha | Kdy startuje |
|-------|----------------|
| `Mobilmajak-CameraGateway-<Nazev>` | start PC (+30 s), přihlášení, **každých 30 min** (záloha) |
| `Mobilmajak-CameraGateway-<Nazev>-WakeKick` | přihlášení, probuzení ze spánku |

**PC vypnutý** = kamera nehlásí (normální).  
**Po zapnutí** = brána nastartuje sama do ~30 s po bootu, nebo po přihlášení, nejpozději do 30 min (periodická úloha).

Ranní kontrola na PC:

```powershell
Get-ScheduledTask -TaskName "Mobilmajak-CameraGateway-Sternberk*" | ft TaskName, State
Get-Content "C:\ProgramData\Mobilmajak\CameraGateway-Sternberk\gateway.log" -Tail 5
```

Očekáváno: `Supervisor start`, `Pripojeno` / `nasloucham`.

**Zlín (15. 6.):** log ukázal restart až v 10:50 – pravděpodobně PC v noci spal / nikdo se nepřihlásil. Mechanismus je stejný.  
Na již nainstalovaném PC spusť aktualizaci (bez přepsání configu):

```cmd
cd C:\Temp\zlin-gateway
update-installed-gateway.cmd
```

## 5. Ověření

```bash
./scripts/camera_motion_test_sternberk.sh isapi
./scripts/camera_motion_test_sternberk.sh motion true
```

MOBILMAJAK → Směny → Není v práci → majáček u prodejny.

## Pilotní prodejny

| Prodejna | slug | ID | NVR |
|----------|------|----|-----|
| Globus | `globus` | 1 | 10.0.0.250 |
| Senimo | `senimo` | 2 | 192.168.1.104 |
| Čepkov / Zlín | `zlin` | 3 | 10.0.0.250 |
| Šternberk | `sternberk` | 6 | 10.0.1.112 |

Nová prodejna = zkopírovat blok v `prodejny.json` + zkopírovat složku `*-gateway` z existující (jen přejmenovat `install-*.ps1`).

## Konvence

| Položka | Hodnota |
|---------|---------|
| `config.json` | vždy obsahuje `prodejna_id` + `prodejna_nazev` |
| PowerShell | ASCII only |
| Spuštění | `.cmd` wrapper nebo `.\install-*.cmd` v PowerShellu |
