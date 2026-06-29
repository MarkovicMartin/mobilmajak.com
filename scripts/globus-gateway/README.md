# Globus – brána pohybu kamer (Windows)

Pilot pro **prodejnu Globus** (`prodejna_id`: **1**).  
Instalace používá sdílený balíček `scripts/camera-gateway/`.

## Síť na místě

| Zařízení | IP |
|----------|-----|
| NVR | `10.0.0.250` |
| IP kamera | `192.168.254.3` |

Brána komunikuje jen s **NVR** (ISAPI alertStream). U kanálu kamery: **Detekce → Propojení → Upozornit iVMS**.

## Checklist

| Krok | Kde | Stav |
|------|-----|------|
| 1. Secret na VPS | `camera_motion_secrets.json` → `"1": "<hex>"` | ☑ |
| 2. Lokální config | `secrets/camera_motion_globus.json` | ☑ |
| 3. USB | `camera-gateway/` + `globus-gateway/` (s `config.json`) | ☐ |
| 4. NVR menu | Upozornit iVMS u kanálu | ☐ |
| 5. Instalace PC | `install-globus-camera-gateway.cmd` (správce) | ☐ |

## Příprava na Macu

```bash
cp secrets/camera_motion_globus.json scripts/globus-gateway/config.json
```

Na USB zkopírovat **obě** složky:

- `scripts/camera-gateway/`
- `scripts/globus-gateway/` (s `config.json`)

Podrobný postup: `POSTUP.txt`

## Instalace na PC v Globusu

```cmd
cd C:\Temp\globus-gateway
install-globus-camera-gateway.cmd
```

Úlohy: `Mobilmajak-CameraGateway-Globus` (+ WakeKick).  
Složka: `C:\ProgramData\Mobilmajak\CameraGateway-Globus`

## Oprava / aktualizace

```cmd
fix-and-restart-globus.cmd      REM skripty + config z USB
update-installed-gateway.cmd    REM jen skripty, config beze změny
uninstall-globus-camera-gateway.cmd
```

## Test z Macu (VPN do LAN)

```bash
./scripts/camera_motion_test_globus.sh isapi
./scripts/camera_motion_test_globus.sh motion true
```

## Ověření v MOBILMAJAK

Směny → **Není v práci** – majáček u Globusu (`in_pilot`, zdroj `gateway`).

Kompletní návod: `scripts/camera-gateway/INSTALL.md`
