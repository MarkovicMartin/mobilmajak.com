# Senimo – brána pohybu kamer (Windows)

> Pro další prodejny s autodetekcí NVR použijte **`scripts/camera-gateway/`** a `install-camera-gateway.ps1 -ProdejnaId …`.

Posílá signály **pohyb / klid** z NVR (`192.168.1.104`) na MOBILMAJAK staging.  
Bez obrazu, bez kabelu do sítě `192.168.254.x`.

## Požadavky na PC v Senimu

- Windows 10/11, **ve Wi‑Fi prodejny** (`192.168.1.x`)
- **Python není potřeba** – instalátor stáhne portable Python (~25 MB, jednorázově)
- **Internet** při instalaci (stažení Pythonu + pip requests)
- V NVR: **Detekce → Propojení → Upozornit iVMS** u kanálu (např. IP kamera2)

## Příprava (jednou, u vás na Macu)

1. Zkopírujte celou složku `scripts/senimo-gateway` na USB / síťový disk.
2. Připravte `config.json` vedle instalátoru (zkopírujte z `secrets/camera_motion_senimo.json` na Macu a přejmenujte):

```json
{
  "mobilmajak_api": "https://mobilmajak.com",
  "prodejna_id": 2,
  "motion_secret": "...",
  "nvr_host": "192.168.1.104",
  "nvr_user": "admin",
  "nvr_pass": "..."
}
```

**`motion_secret`** musí být **stejný** jako v `camera_motion_secrets.json` na produkčním VPS.

Kompletní návod: `scripts/camera-gateway/INSTALL.md`

## Instalace na pokladním PC

1. Zkopírujte složku `senimo-gateway` na PC (např. `C:\Temp\senimo-gateway`).
2. Pravý klik na **PowerShell (správce)** nebo **Příkazový řádek (správce)**.
3. **Nejjednodušší** – dvojklik nebo z cmd (obejde „running scripts are disabled“):

```cmd
cd C:\Users\uživatel\Downloads\senimo-gateway\senimo-gateway
install-senimo-camera-gateway.cmd
```

Alternativa v PowerShellu:

```powershell
cd C:\Temp\senimo-gateway
powershell -ExecutionPolicy Bypass -File .\install-senimo-camera-gateway.ps1
```

Pokud Windows blokuje stažené soubory:

```powershell
Get-ChildItem . | Unblock-File
```

4. Skript nainstaluje do `C:\ProgramData\Mobilmajak\SenimoCameraGateway`, vytvoří úlohy:
   - **Mobilmajak-Senimo-CameraGateway** – brána (start +30 s, přihlášení, záloha každých 30 min)
   - **Mobilmajak-Senimo-CameraGateway-WakeKick** – po probuzení ze spánku bránu restartuje
5. Ověří ISAPI a test na staging.

## Ruční spuštění / log

```powershell
Start-ScheduledTask -TaskName 'Mobilmajak-Senimo-CameraGateway'
Get-Content C:\ProgramData\Mobilmajak\SenimoCameraGateway\gateway.log -Tail 30 -Wait
```

V logu by měly být řádky `stale nasloucham` každých ~60 s. Po probuzení PC ze spánku i `wake-kick: restarting`.

**Spánek přes noc:** brána během spánku nefunguje (PC je vypnutý softwareově), ale po probuzení se **automaticky restartuje** (WakeKick úloha). Záložní kontrola každých 30 min spustí bránu, pokud neběží.

## Aktualizace na již nainstalovaném PC

Zkopírujte novou složku `senimo-gateway` na USB a na PC (správce):

```cmd
cd C:\Temp\senimo-gateway
update-installed-gateway.cmd
```

Nepřepisuje `config.json`. Restartuje úlohu Plánovače.

## Ověření v MOBILMAJAK

Staging → **Směny → Není v práci → Pilot kamer – stav** u Senima.  
Nové záznamy se zdrojem **`gateway`** po pohybu před kamerou.

## Odinstalace

```powershell
cd C:\Temp\senimo-gateway
.\uninstall-senimo-camera-gateway.ps1
```

## Řešení problémů

| Problém | Řešení |
|---------|--------|
| ISAPI test selže | PC musí být v `192.168.1.x`, ping na `192.168.1.104` |
| Jen `test`, ne `gateway` | Brána neběží nebo v NVR chybí **Upozornit iVMS** |
| Stažení Pythonu selže | Zkontrolujte internet; případně spusťte instalaci znovu |
| *running scripts are disabled* | Spusťte `install-senimo-camera-gateway.cmd` nebo `powershell -ExecutionPolicy Bypass -File .\install-senimo-camera-gateway.ps1` |
