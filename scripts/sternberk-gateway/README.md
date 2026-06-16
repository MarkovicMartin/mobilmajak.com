# Šternberk – brána pohybu kamer (Windows)

Pilot pro **prodejnu Šternberk** (`prodejna_id`: **6**).  
Instalace používá sdílený balíček `scripts/camera-gateway/`.

## Síť na místě

| Zařízení | IP |
|----------|-----|
| NVR | `10.0.1.112` |
| IP kamera | `192.168.254.6` |

Brána komunikuje jen s **NVR** (ISAPI alertStream). Kamera musí být v NVR přidaná a u kanálu zapnuté **Detekce → Propojení → Upozornit iVMS**.

## Checklist (doplňovat postupně)

| Krok | Kde | Stav |
|------|-----|------|
| 1. Vygenerovat secret | VPS: `openssl rand -hex 32` | ☑ |
| 2. Přidat do VPS | `/home/webmajak/secrets/camera_motion_secrets.json` → `"6": "<hex>"` | ☑ |
| 3. Restart API | `systemctl restart webmajak` | ☐ |
| 4. Lokální config | `secrets/camera_motion_sternberk.json` (viz níže) | ☑ |
| 5. `motion_secret` | stejný hex jako v kroku 2 | ☑ |
| 6. NVR | `nvr_pass`, `nvr_host` = `10.0.1.112` | ☑ |
| 7. USB | zkopírovat `scripts/camera-gateway` + `scripts/sternberk-gateway` | ☐ |
| 8. Instalace na PC | `install-sternberk-camera-gateway.cmd` (správce) | ☐ |

## Příprava na Macu

```bash
cp scripts/sternberk-gateway/config.example.json secrets/camera_motion_sternberk.json
# upravte motion_secret, nvr_pass

cp secrets/camera_motion_sternberk.json scripts/sternberk-gateway/config.json
```

Na USB zkopírujte **obě** složky:

- `scripts/camera-gateway/`
- `scripts/sternberk-gateway/` (s `config.json`)

Kompletní návod: `scripts/camera-gateway/INSTALL.md`

## Instalace na PC ve Šternberku

1. Zkopírujte obě složky na PC (např. `C:\Temp\`).
2. Spusťte **cmd jako správce**:

```cmd
cd C:\Temp\sternberk-gateway
install-sternberk-camera-gateway.cmd
```

Úlohy Plánovače: `Mobilmajak-CameraGateway-Sternberk` (+ WakeKick).  
Složka: `C:\ProgramData\Mobilmajak\CameraGateway-Sternberk`

## Test z Macu (VPN do LAN nebo na místě)

```bash
chmod +x scripts/camera_motion_test_sternberk.sh
./scripts/camera_motion_test_sternberk.sh isapi
./scripts/camera_motion_test_sternberk.sh motion true
```

## Ověření v MOBILMAJAK

Dashboard **Kdo je dnes v práci** nebo Směny → **Není v práci** – majáček u Šternberka (`in_pilot`).

## Aktualizace / odinstalace

```cmd
update-installed-gateway.cmd
uninstall-sternberk-camera-gateway.cmd
```

Nepřepisuje `config.json` v `ProgramData`.
