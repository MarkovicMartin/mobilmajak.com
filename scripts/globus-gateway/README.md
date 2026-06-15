# Globus – brána pohybu kamer (Windows)

Pilot pro **prodejnu Globus** (`prodejna_id`: **1**).  
Instalace používá sdílený balíček `scripts/camera-gateway/`.

## Checklist (doplňovat postupně)

| Krok | Kde | Stav |
|------|-----|------|
| 1. Vygenerovat secret | VPS: `openssl rand -hex 32` | ☐ |
| 2. Přidat do VPS | `/home/webmajak/secrets/camera_motion_secrets.json` → `"1": "<hex>"` | ☐ |
| 3. Restart API | `systemctl restart webmajak` | ☐ |
| 4. Lokální config | `cp secrets/camera_motion_globus.example.json secrets/camera_motion_globus.json` + doplnit | ☐ |
| 5. `motion_secret` | stejný hex jako v kroku 2 | ☐ |
| 6. NVR | `nvr_pass`, případně `nvr_host` pokud autodetekce selže | ☐ |
| 7. USB | zkopírovat `scripts/camera-gateway` + `scripts/globus-gateway` | ☐ |
| 8. Instalace na PC | `install-globus-camera-gateway.cmd` (správce) | ☐ |

## Příprava na Macu

```bash
cp secrets/camera_motion_globus.example.json secrets/camera_motion_globus.json
# upravte motion_secret, nvr_pass, nvr_host dle potřeby

cp secrets/camera_motion_globus.json scripts/globus-gateway/config.json
```

Na USB zkopírujte **obě** složky:

- `scripts/camera-gateway/`
- `scripts/globus-gateway/` (s `config.json`)

Kompletní návod: `scripts/camera-gateway/INSTALL.md`

## Instalace na PC v Globusu

1. Zkopírujte obě složky na PC (např. `C:\Temp\`).
2. Spusťte **cmd jako správce**:

```cmd
cd C:\Temp\globus-gateway
install-globus-camera-gateway.cmd
```

Úlohy Plánovače: `Mobilmajak-CameraGateway-Globus` (+ WakeKick).  
Složka: `C:\ProgramData\Mobilmajak\CameraGateway-Globus`

## Test z Macu (po doplnění config)

```bash
chmod +x scripts/camera_motion_test_globus.sh
./scripts/camera_motion_test_globus.sh isapi
./scripts/camera_motion_test_globus.sh motion true
```

## Ověření v MOBILMAJAK

Dashboard **Kdo je dnes v práci** nebo Směny → **Není v práci** – majáček u Globusu (`in_pilot`).

## Aktualizace / odinstalace

```cmd
update-installed-gateway.cmd
uninstall-globus-camera-gateway.cmd
```

Nepřepisuje `config.json` v `ProgramData`.
