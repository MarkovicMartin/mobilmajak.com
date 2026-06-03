"""
Návrh ověření přítomnosti přes Hikvision / HiLook (bez veřejného streamu v MOBILMAJAK).

Současný stav
-------------
- Kamery jsou dostupné operátorům přes mobilní aplikaci Hik-Connect / iVMS.
- Obraz není sdílen přes veřejné IP do internetu (správně z hlediska bezpečnosti).

Doporučená architektura (fáze 2–3)
----------------------------------
1. **Lokální brána na síti prodejny** (mini-PC / NVR ve stejné VLAN jako kamery)
   - ISAPI / SDK Hikvision pouze z interní sítě.
   - Žádný port forwarding RTSP na internet.

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

Fáze 1 (nyní)
-------------
- Přehled „Není v práci“ pouze z docházky (příchod v aplikaci).
- Kamera: statický status `planned` v API odpovědi.

Implementační kroky pro fázi 2
------------------------------
- [ ] NVR/gateway skript: poll ISAPI `/ISAPI/System/Video/inputs/channels` nebo event stream.
- [ ] Webhook `POST /api/shifts/camera-events/` (HMAC podpis).
- [ ] Admin UI: sloupec „Kamera“ u prodejny (🟢 pohyb / ⚪ ticho / ❓ offline).
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
    """Stav integrace kamer pro API (zatím bez live napojení)."""
    return {
        'enabled': False,
        'phase': 'planned',
        'label': 'Kontrola kamer (Hikvision) – připravuje se',
        'hint': (
            'Ověření přes lokální bránu v síti prodejny (ISAPI události / jas scény). '
            'Bez veřejného RTSP do aplikace.'
        ),
        'nvr_access': NVR_ACCESS_GUIDE,
    }
