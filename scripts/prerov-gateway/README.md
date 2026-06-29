# Přerov – brána pohybu kamer (Windows)

Pilot pro **prodejnu Přerov** (`prodejna_id`: **4**).  
Instalace používá sdílený balíček `scripts/camera-gateway/`.

## Síť na místě

| Zařízení | IP |
|----------|-----|
| NVR | `10.0.0.90` |
| IP kamera | `10.0.0.3` |

Brána komunikuje jen s **NVR** (ISAPI alertStream). U kanálu: **Detekce → Propojení → Upozornit iVMS**.

## Checklist

| Krok | Kde | Stav |
|------|-----|------|
| 1. Secret na VPS | `"4"` v `camera_motion_secrets.json` | ☑ |
| 2. Lokální config | `secrets/camera_motion_prerov.json` | ☑ |
| 3. USB | `camera-gateway/` + `prerov-gateway/` (s `config.json`) | ☐ |
| 4. NVR menu | Upozornit iVMS | ☐ |
| 5. Instalace PC | `install-prerov-camera-gateway.cmd` | ☐ |

## Příprava na Macu

```bash
cp secrets/camera_motion_prerov.json scripts/prerov-gateway/config.json
```

Na USB **obě** složky. Podrobný postup: `POSTUP.txt`

## Instalace na PC v Přerově

```cmd
cd C:\Temp\prerov-gateway
install-prerov-camera-gateway.cmd
```

Volitelně ověření IP: `02-discover-lan.cmd`

Úlohy: `Mobilmajak-CameraGateway-Prerov` (+ WakeKick).  
Složka: `C:\ProgramData\Mobilmajak\CameraGateway-Prerov`

## Oprava / aktualizace

```cmd
fix-and-restart-prerov.cmd
update-installed-gateway.cmd
uninstall-prerov-camera-gateway.cmd
```

## Test z Macu (VPN do LAN)

```bash
./scripts/camera_motion_test_prerov.sh isapi
./scripts/camera_motion_test_prerov.sh motion true
```

Kompletní návod: `scripts/camera-gateway/INSTALL.md`
