# Deploy status — servismajak.cz (vzhled)

Aktualizováno: 2026-11-25

## Wave 1 — NASAZENO

| Krok | published | historyId | Nová version |
|------|-----------|-----------|--------------|
| design barvy | true | 963 | `5d919009700bd445cae77784200431c91b2c452e9af486a80e901a8e901698d4` |
| scripts.head overlay | true | 964 | `e8d284be1baeb1d43cb42d1b57a7a847f94b43f3f8c48d56c70fd205824f2a30` |

### Smoke (live)

| Kontrola | Výsledek |
|----------|----------|
| `#mm-brand-overlay` na homepage | OK |
| Open Sans | OK |
| `.btn-primary` = `rgb(47, 91, 255)` | OK |
| WhatsApp FAB | OK |
| Detail produktu + Rezervovat | OK |

### Rollback

PATCH z `backup/design.json` + `backup/scripts.json` (po novém GET `version`):

- design backup version: `2fd97e0095ac6712d79e8cc8348cfbc9950dfe223f68a36378730d1979374f37`
- scripts backup version: `e6bfcd6abbf648bd267aff700d2cb15ea29686b3b19e47dc52034a344e2ab5f1`

## Wave 2 — NASAZENO

| Krok | record | historyId | Nová version |
|------|--------|-----------|--------------|
| SYS-3 karty služeb | contents/32 | 19 | `1465bc42ca236b5e7065b72754b5918df4d1fd879185bea1b68f9d311c04fd99` |
| SYS-2 karty (alt výpis) | contents/29 | 20 | `a79599665343a97fb31589cc0d6be8d65b6340fe626b6f8cb0de8a6715ca18e9` |
| SYS-1 (obsah 47) | contents/47 | 21 | `8b28a010dfc33463edb4336b42f11b4c1386f4e733b4fa00cc5386c1178be6c6` |
| SYS-1 live na /zarizeni/ | contents/56 | 22 | `d954d6315ff38fad1282cb4d90dfe47c60b193cfaa47d5ed3a56fef579fa8801` |
| Homepage vítejte | contents/8 | 23 | `c7d81ff2408e43a626c23ba80d8349ea4cc146db60b741ebc0939570161cd22e` |
| scripts.head (CTA + product suggest) | scripts | 965 | `e0ec7192f5e25a0698711985311652866af5e4e624ddbe3f085ff403b97bd55a` |

### Smoke (live)

| Kontrola | Výsledek |
|----------|----------|
| `/zarizeni/iphone-13` → `.mm-svc-card` + Rezervovat | OK |
| `/zarizeni/mobilni-telefony` → `.mm-cat-card` (9) | OK |
| Homepage H1 „Rozbil se? My ho opravíme.“ | OK |
| CTA Zjistit cenu / Najít pobočku | OK |
| `#mm-brand-overlay` + `.mm-search-suggest` DOM | OK |

### Rollback wave 2

1. GET aktuální `version` u contents 8/29/32/47/56 + scripts
2. PATCH HTML z `backup/contents-*-*.html` / pre-wave2 versions v `backup/contents-*.json`
3. scripts: vrátit wave1 head (`wave1/scripts.head.html`) nebo `backup/scripts.json`

Pre-wave2 versions:

- SYS-2/29: `4027c6a8794986487b598baeba7726c46e3796ab5e4db7fa325b45d033085cf6`
- SYS-3/32: `337ada0f8530c0b1b4f9a0ca534496be82f738c1a06f3f2da1ee4c831971cc88`
- SYS-1/47: `3aad9e40c35dbe7ef673d97e5723277135459eff1cdd82949a9f4b459fa7cd75`
- SYS-1/56: `2756b20064d6312600bed6296be0291015c3f3e789e38961bd0ce5002f9dc39d`
- home/8: `d148318b1551c2a1928da30deedc44de2209e5d8106678789620b5e619cb5dae`
- scripts (wave1): `e8d284be1baeb1d43cb42d1b57a7a847f94b43f3f8c48d56c70fd205824f2a30`

### Poznámky

- Plný hero finder (4 kroky) **není** nasazen — top search product suggest ano
- Related products na detailu odloženo

## Wave 3 — NASAZENO

Homepage layout dle `novy-navrh` (hero + finder + trust + process + problems), CSS/JS overlay, skryté legacy bloky.

| Krok | record | historyId | Poznámka |
|------|--------|-----------|----------|
| Homepage HTML + devices JSON | contents/8 | (wave3) | `#mm-home` hero/finder |
| scripts.head overlay | scripts | 966 | wave3 CSS/JS (≤64 KB) |
| Home block full-width | blocks/23 | 28 | `col-12` + `p-0` |
| Hide O nás | blocks/68 | 29 | `visible:false` |
| Hide SYS-10 banner | blocks/77 | 30 | `visible:false` |
| Hide legacy | blocks/24,27,74 | earlier | `visible:false` |

### Smoke (live)

| Kontrola | Výsledek |
|----------|----------|
| `#mm-home` + `.mm-hero` + `[data-mm-finder]` | OK |
| `#mm-announce` lišta | OK |
| Finder: typ → Apple → iPhone 13 → 13 služeb | OK |
| CTA po modelu → `/zarizeni/iphone-13` | OK |
| SYS-10 „Šplouchá…“ skrytý | OK |
| O nás (block 68) skrytý | OK |

### Rollback wave 3

1. GET aktuální `version` u contents/8, scripts, blocks 23/24/27/68/74/77
2. contents/8: vrátit wave2 HTML / `backup`
3. scripts: `wave2/scripts.head.html`
4. blocks: obnovit `visible` / col dle pre-wave3

### Poznámky wave 3

- MyRepair chrome (header search, nav) zůstává — overlay jen styluje
- Related products / katalog detail polish stále odloženo
- Pobočky blok na homepage zůstává (nativní)

## Wave 3b — opravy (2026-11-25)

| Krok | record | historyId |
|------|--------|-----------|
| scripts: z-index finder > trust, bílá CTA, SYS-3 row CSS | scripts | 968 |
| SYS-3 řádky (název · cena · čas · Rezervovat) | contents/32 | 31 |

Smoke: `/zarizeni/iphone-16e` → `.mm-service-row` + Rezervovat `color:#fff` / `bg:#2F5BFF`; homepage finder panel nad `.mm-trust`.
