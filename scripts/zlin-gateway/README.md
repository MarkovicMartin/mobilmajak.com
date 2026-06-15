# Čepkov (Zlín) – brána pohybu kamer (Windows)

Pilot pro **prodejnu Čepkov / Zlín** (`prodejna_id`: **3**).  
Instalace používá sdílený balíček `scripts/camera-gateway/`.

## Síť na místě

| Zařízení | IP |
|----------|-----|
| NVR | `10.0.0.250` |
| IP kamera | `10.0.0.246` |

Brána komunikuje jen s **NVR** (ISAPI alertStream). Kamera musí být v NVR přidaná a u kanálu zapnuté **Detekce → Propojení → Upozornit iVMS**.

## Checklist (doplňovat postupně)

| Krok | Kde | Stav |
|------|-----|------|
| 1. Vygenerovat secret | VPS: `openssl rand -hex 32` | ☐ |
| 2. Přidat do VPS | `/home/webmajak/secrets/camera_motion_secrets.json` → `"3": "<hex>"` | ☐ |
| 3. Restart API | `systemctl restart webmajak` | ☐ |
| 4. Lokální config | `secrets/camera_motion_zlin.json` (viz níže) | ☐ |
| 5. `motion_secret` | stejný hex jako v kroku 2 | ☐ |
| 6. NVR | `nvr_pass`, `nvr_host` = `10.0.0.250` | ☐ |
| 7. USB | zkopírovat `scripts/camera-gateway` + `scripts/zlin-gateway` | ☐ |
| 8. Instalace na PC | `install-zlin-camera-gateway.cmd` (správce) | ☐ |

## Příprava na Macu

```bash
cp scripts/zlin-gateway/config.example.json secrets/camera_motion_zlin.json
# upravte motion_secret, nvr_pass

cp secrets/camera_motion_zlin.json scripts/zlin-gateway/config.json
```

Na USB zkopírujte **obě** složky:

- `scripts/camera-gateway/`
- `scripts/zlin-gateway/` (s `config.json`)

Kompletní návod: `scripts/camera-gateway/INSTALL.md`

## Instalace na PC v Čepkově

1. Zkopírujte obě složky na PC (např. `C:\Temp\`).
2. Spusťte **cmd jako správce**:

```cmd
cd C:\Temp\zlin-gateway
install-zlin-camera-gateway.cmd
```

Úlohy Plánovače: `Mobilmajak-CameraGateway-Zlin` (+ WakeKick).  
Složka: `C:\ProgramData\Mobilmajak\CameraGateway-Zlin`

## Test z Macu (VPN do LAN nebo na místě)

```bash
chmod +x scripts/camera_motion_test_zlin.sh
./scripts/camera_motion_test_zlin.sh isapi
./scripts/camera_motion_test_zlin.sh motion true
```

## Ověření v MOBILMAJAK

Dashboard **Kdo je dnes v práci** nebo Směny → **Není v práci** – majáček u Čepkova (`in_pilot`).

## Aktualizace / odinstalace

```cmd
update-installed-gateway.cmd
uninstall-zlin-camera-gateway.cmd
```

Nepřepisuje `config.json` v `ProgramData`.
