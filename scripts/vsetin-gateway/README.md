# Vsetín – brána pohybu kamer (Windows)

Pilot pro **prodejnu Vsetín** (`prodejna_id`: **5**).  
Instalace používá sdílený balíček `scripts/camera-gateway/`.

## Checklist

| Krok | Kde | Stav |
|------|-----|------|
| 1. Secret na VPS | `"5": "7f5b49e3…"` v `camera_motion_secrets.json` | ☐ |
| 2. Restart API | `systemctl restart webmajak` | ☐ |
| 3. Lokální config | `secrets/camera_motion_vsetin.json` | ☑ |
| 4. IP NVR/kamera | `02-discover-lan.cmd` na PC ve Vsetíně | ☐ |
| 5. USB | `camera-gateway/` + `vsetin-gateway/` (s `config.json`) | ☐ |
| 6. NVR menu | Upozornit iVMS u kanálu | ☐ |
| 7. Instalace PC | `install-vsetin-camera-gateway.cmd` | ☐ |

## Příprava na Macu

```bash
cp secrets/camera_motion_vsetin.json scripts/vsetin-gateway/config.json
```

Na USB **obě** složky. Podrobný postup: `POSTUP.txt`

## Instalace na PC ve Vsetíně

1. `02-discover-lan.cmd` → doplnit IP do `config.json`
2. CMD jako správce:

```cmd
cd C:\Temp\vsetin-gateway
install-vsetin-camera-gateway.cmd
```

Úlohy: `Mobilmajak-CameraGateway-Vsetin` (+ WakeKick).  
Složka: `C:\ProgramData\Mobilmajak\CameraGateway-Vsetin`

## Oprava / aktualizace

```cmd
fix-and-restart-vsetin.cmd
update-installed-gateway.cmd
uninstall-vsetin-camera-gateway.cmd
```

## Test z Macu (VPN do LAN)

```bash
./scripts/camera_motion_test_vsetin.sh isapi
./scripts/camera_motion_test_vsetin.sh motion true
```

Kompletní návod: `scripts/camera-gateway/INSTALL.md`
