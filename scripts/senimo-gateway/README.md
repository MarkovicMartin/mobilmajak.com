# Senimo – brána pohybu kamer (Windows)

Pilot pro **prodejnu Senimo** (`prodejna_id`: **2**).  
Instalace používá sdílený balíček `scripts/camera-gateway/` (stejně jako Šternberk a Zlín).

## Síť na místě

| Zařízení | IP |
|----------|-----|
| NVR | `192.168.1.100` |

Brána komunikuje jen s **NVR** (ISAPI alertStream). U kanálu kamery: **Detekce → Propojení → Upozornit iVMS**.

## Oprava na již nainstalovaném PC (nejčastější)

1. USB: zkopírovat **`scripts/camera-gateway`** + **`scripts/senimo-gateway`**
2. CMD jako správce:

```cmd
cd C:\Temp\senimo-gateway
fix-and-restart-senimo.cmd
```

Podrobný postup: `POSTUP.txt`

## Nová instalace

```bash
cp -R scripts/camera-gateway scripts/senimo-gateway /Volumes/USB/
cp secrets/camera_motion_senimo.json /Volumes/USB/senimo-gateway/config.json
# doplnit nvr_pass v secrets/ pred kopirovanim
```

Na USB obě složky `camera-gateway/` + `senimo-gateway/` (s `config.json` ze `secrets/`)

```cmd
cd C:\Temp\senimo-gateway
install-senimo-camera-gateway.cmd
```

Úlohy Plánovače: `Mobilmajak-Senimo-CameraGateway` (+ WakeKick).  
Složka: `C:\ProgramData\Mobilmajak\SenimoCameraGateway`

## Aktualizace / odinstalace

```cmd
update-installed-gateway.cmd
uninstall-senimo-camera-gateway.cmd
```

Nepřepisuje `config.json` v ProgramData.

Kompletní návod: `scripts/camera-gateway/INSTALL.md`
