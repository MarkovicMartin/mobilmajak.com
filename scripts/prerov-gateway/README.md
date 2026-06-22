# Přerov – brána pohybu kamer (Windows)

Pilot pro **prodejnu Přerov** (`prodejna_id`: **4**).  
Instalace používá sdílený balíček `scripts/camera-gateway/`.

## Síť na místě

| Zařízení | IP |
|----------|-----|
| NVR | `DOPLNTE_IP_NVR` |
| IP kamera | `DOPLNTE_IP_KAMERY` |

Brána komunikuje jen s **NVR** (ISAPI alertStream). Kamera musí být v NVR přidaná a u kanálu zapnuté **Detekce → Propojení → Upozornit iVMS**.

## Checklist (doplňovat postupně)

| Krok | Kde | Stav |
|------|-----|------|
| 1. Vygenerovat secret | VPS: `openssl rand -hex 32` | ☐ |
| 2. Přidat do VPS | `/home/webmajak/secrets/camera_motion_secrets.json` → `"4": "<hex>"` | ☐ |
| 3. Restart API | `systemctl restart webmajak` | ☐ |
| 4. Lokální config | `secrets/camera_motion_prerov.json` | ☐ |
| 5. `motion_secret` | stejný hex jako v kroku 2 | ☐ |
| 6. NVR | `nvr_pass`, `nvr_host`, `camera_host` | ☐ |
| 7. USB | zkopírovat `scripts/camera-gateway` + `scripts/prerov-gateway` | ☐ |
| 8. Instalace na PC | `install-prerov-camera-gateway.cmd` (správce) | ☐ |

## Příprava na Macu

```bash
# Doplňte IP v scripts/camera-gateway/prodejny.json (blok prerov), pak:
./scripts/prepare-camera-gateway.sh prerov
# nebo rovnou na USB:
./scripts/prepare-camera-gateway.sh prerov /Volumes/USB
```

Ručně:

```bash
cp scripts/prerov-gateway/config.example.json secrets/camera_motion_prerov.json
# upravte motion_secret, nvr_host, camera_host, nvr_pass

cp -R scripts/camera-gateway scripts/prerov-gateway /Volumes/USB/
cp secrets/camera_motion_prerov.json /Volumes/USB/prerov-gateway/config.json
```

Na USB zkopírujte **obě** složky:

- `camera-gateway/`
- `prerov-gateway/` (s `config.json` ze `secrets/`)

Kompletní návod: `scripts/camera-gateway/INSTALL.md`

## Instalace na PC v Přerově

1. Zkopírujte obě složky na PC (např. `C:\Temp\`).
2. Spusťte **cmd jako správce**:

```cmd
cd C:\Temp\prerov-gateway
install-prerov-camera-gateway.cmd
```

Úlohy Plánovače: `Mobilmajak-CameraGateway-Prerov` (+ WakeKick).  
Složka: `C:\ProgramData\Mobilmajak\CameraGateway-Prerov`

## Test z Macu (VPN do LAN nebo na místě)

**Bez monitoru u NVR** – z PC/Mac ve stejné síti jako NVR:

```bash
chmod +x scripts/camera_motion_discover_lan.sh
./scripts/camera_motion_discover_lan.sh secrets/camera_motion_prerov.json
```

Najde NVR, samostatné IP kamery (IPC) a kamery připojené k NVR (včetně PoE sítě `192.168.254.x`).

Pokud sken nic nenajde, doplňte podsítě do configu:

```json
"autodiscover_subnets": ["192.168.1.0/24", "10.0.1.0/24"]
```

```bash
chmod +x scripts/camera_motion_test_prerov.sh
./scripts/camera_motion_test_prerov.sh isapi
./scripts/camera_motion_test_prerov.sh motion true
```

## Ověření v MOBILMAJAK

Dashboard **Kdo je dnes v práci** nebo Směny → **Není v práci** – majáček u Přerova (`in_pilot`).

## Aktualizace / odinstalace

```cmd
update-installed-gateway.cmd
uninstall-prerov-camera-gateway.cmd
```

Nepřepisuje `config.json` v `ProgramData`.
