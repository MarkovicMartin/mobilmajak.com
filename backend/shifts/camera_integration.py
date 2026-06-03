"""
Návrh ověření přítomnosti přes Hikvision / HiLook (bez veřejného streamu v MOBILMAJAK).

Současný stav
-------------
- Kamery jsou dostupné operátorům přes mobilní aplikaci Hik-Connect / iVMS.
- Obraz není sdílen přes veřejné IP do internetu (správně z hlediska bezpečnosti).

Doporučená architektura (fáze 2–3)
----------------------------------
**Potřebujete další PC na prodejně?** Ne – stačí **NVR** (běží pořád) a kamery. Samotný VPS ale NVR
**neuvidí**, pokud má jen soukromou IP (192.168.x.x) a neotevíráte ji na internet. Nutná je
**síťová cesta ze serveru k NVR** (viz níže), ne druhý počítač v prodejně.

| Varianta | Extra PC na prodejně | Co běží |
|--------|----------------------|---------|
| **A – VPN (doporučeno)** | Ne | NVR + VPN (router / Tailscale na NVR nebo bráně). VPS polluje ISAPI přes tunel. |
| **B – Mini brána** | Ano (Raspberry / starý mini-PC) | Skript v LAN posílá webhooky na VPS. |
| **C – Hik-Connect cloud** | Ne | NVR v účtu Hik-Connect; VPS volá Hikvision cloud API (závislost na účtu/limitech). |

1. **Cíl: ISAPI na NVR** (Hikvision / HiLook – stejné rozhraní u většiny NVR)
   - Žádný veřejný RTSP / port forwarding do internetu.
   - Ze serveru jen HTTP(S) požadavky (stav, události pohybu, případně jas snímku).

2. **Signály pro docházku (bez live videa v prohlížeči)**
   a) **Pohyb / obsazení** – ISAPI event subscription (line crossing, VMD) → webhook na backend.
   b) **„Rozsvíceno“** – jedna referenční kamera na prodejnu + průměr jasu snímku (1×/5 min),
      nebo smart zásuvka / relé osvětlení s MQTT, pokud je k dispozici.
   c) **Volitelně** – počet osob z lokálního AI (Hikvision AcuSense) jako binární „někdo v prodejně“.

3. **Backend MOBILMAJAK**
   - Tabulka `ProdejnaKamera` (prodejna_id, nazev, vnitrni_url, kanal, aktivni).
   - Tabulka `KameraUdalost` (prodejna_id, typ: pohyb|svetlo|offline, cas, payload_json).
   - Endpoint pro admin: srovnání „chybí příchod“ vs „kamera hlásí pohyb za posledních N min“.

4. **Bezpečnost**
   - Credentials jen v `secrets/` na VPS nebo na bráně; rotace hesel ISAPI.
   - Audit log kdo otevřel náhled (pokud později přidáme zabezpečený proxy náhled pro admina).

Alternativa bez kamer: PC na prodejně (heartbeat)
-----------------------------------------------
- Při **zapnutí / přihlášení / probuzení** malý skript (Plánovač úloh / systemd) pošle
  `POST` na backend (token per prodejna, HMAC) – **odchozí** spojení, VPN nepotřebujete.
- Vhodné jako **doplňkový** signál („technické spuštění“), ne náhrada příchodu v aplikaci.
- **Usínání PC:** při spánku heartbeat ustane → falešné „prodejna zavřená“; probuzení musí
  spouštět další úlohu (Windows: událost Resume). Někdo může být v práci i s uspaným PC.
- Zapnutí PC ≠ prodejce zaklikl příchod (úklid, aktualizace, kolega bez přihlášení).

Fáze 1 (nyní)
-------------
- Přehled „Není v práci“ pouze z docházky (příchod v aplikaci).
- Kamera / PC heartbeat: statický status `planned` v API odpovědi.

Implementační kroky (pilot pohybu – hotovo v kódu)
--------------------------------------------------
- [x] Webhook `POST /api/shifts/camera-events/` (HMAC, bez obrazu).
- [x] Tabulka `ProdejnaPohybUdalost`, vyhodnocení pohyb/klid v okně N minut.
- [x] Admin UI „Není v práci“: štítek pohybu u prodejny.
- [ ] Brána na prodejně: `scripts/camera_motion_gateway.py` + ISAPI k NVR.
- [ ] `CAMERA_MOTION_SECRETS` na VPS (viz `secrets/README.md`).
"""


NVR_ACCESS_GUIDE = {
    'title': 'Jak se přihlásit k NVR (Hikvision / HiLook)',
    'note': (
        'NVR je v lokální síti prodejny – z internetu ani z MOBILMAJAK se nepřihlásíte. '
        'Potřebujete být ve stejné Wi‑Fi / LAN, nebo na VPN do sítě prodejny.'
    ),
    'methods': [
        {
            'name': 'Mobil – Hik-Connect',
            'steps': [
                'Nainstalujte aplikaci Hik-Connect (oficiální od Hikvision).',
                'Na prodejně musí být NVR přidaný do účtu (QR kód z NVR menu, nebo pozvánka od správce).',
                'Přihlášení e-mailem / telefonem, který správce NVR zaregistroval.',
                'Bez registrace v Hik-Connect uvidíte jen zařízení, která vám někdo „sdílí“.',
            ],
        },
        {
            'name': 'PC – webové rozhraní NVR',
            'steps': [
                'Zjistěte lokální IP NVR (štítek na zařízení, router DHCP, nebo zeptejte IT).',
                'V prohlížeči na PC ve stejné síti: http://IP-NVR (někdy port :80 nebo :443).',
                'Výchozí uživatel bývá admin – heslo nastavil instalatér při prvním spuštění (ne výchozí 12345).',
                'Po prvním přihlášení systém často vyžaduje změnu hesla a bezpečnostní otázku.',
            ],
        },
        {
            'name': 'PC – iVMS-4200 (klasický klient)',
            'steps': [
                'Stáhněte iVMS-4200 z webu Hikvision (verze pro váš OS).',
                'Přidejte zařízení: IP adresa NVR, port 8000 (SDK), uživatel a heslo jako u webu.',
                'Užitečné pro živý náhled a export záznamů na monitoru v kanceláři v síti prodejny.',
            ],
        },
    ],
    'where_to_get_credentials': [
        'Heslo k NVR drží vedoucí prodejny / firma, která kamerový systém instalovala.',
        'Pokud nikdo heslo nezná: reset na NVR (fyzické tlačítko / SADP tool) – jen s povolením vedení.',
        'Do MOBILMAJAK hesla NVR neukládáme; později jen technický účet pro automatické signály (ISAPI).',
    ],
}


def camera_module_status():
    """Stav integrace kamer pro API."""
    from .camera_motion import (
        MOTION_WINDOW_MINUTES,
        load_motion_secrets,
        motion_pilot_prodejna_ids,
    )

    secrets = load_motion_secrets()
    pilot_ids = motion_pilot_prodejna_ids()
    enabled = bool(secrets)
    return {
        'enabled': enabled,
        'phase': 'pilot' if enabled else 'planned',
        'label': (
            'Pilot pohybu na kameře (bez streamu obrazu)'
            if enabled
            else 'Kontrola kamer (Hikvision) – připravuje se'
        ),
        'hint': (
            'Brána v LAN posílá jen „pohyb“ / „klid“. Obraz zůstává na NVR. '
            f'Pilot prodejny: {", ".join(str(i) for i in pilot_ids) or "— (nastavte CAMERA_MOTION_SECRETS)"}.'
            if enabled
            else (
                'Ověření přes lokální bránu v síti prodejny (ISAPI události). '
                'Bez veřejného RTSP do aplikace.'
            )
        ),
        'motion_window_minutes': MOTION_WINDOW_MINUTES,
        'nvr_access': NVR_ACCESS_GUIDE,
    }
