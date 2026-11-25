# Deploy status — servismajak.cz (vzhled)

Aktualizováno: 2026-11-23

## Preview audit

| Kontrola | Výsledek |
|----------|----------|
| HTTP 200 hlavní stránky | OK |
| Lokální odkazy / assety | OK (0 broken) |
| `preview.js` syntax | OK |
| Top search → live produkt | OK (`/ajax/search`) |
| Hero A → live produkt | OK |
| Z-index header / finder / trust-row | OK |
| Rating ★ + „z 5“ | OK |

### Známá omezení preview (neblokují wave 1)

1. Finder CTA na homepage vede na statické `oprava-v2.html` (preview only) — na live zůstane MyRepair detail.
2. Staré HTML (`blog.html`, `hledani.html`…) jsou v složce, ale `index.html` → `novy-navrh.html`.
3. Celý preview SPA **nejde** nahrát 1:1 do MyRepair — nasazuje se vzhled přes šablony/CSS.

## Záloha (rollback)

Složka: `deploy/backup/`

| Soubor | Live version (před wave 1) |
|--------|----------------------------|
| `design.json` | `2fd97e0095ac6712d79e8cc8348cfbc9950dfe223f68a36378730d1979374f37` |
| `scripts.json` | `e6bfcd6abbf648bd267aff700d2cb15ea29686b3b19e47dc52034a344e2ab5f1` |

Rollback = PATCH stejných `data` z backupu (po novém GET `version`).

## dryRun (2026-11-23)

| Krok | dryRun | published | Stav |
|------|--------|-----------|------|
| design barvy | true | false | **PASS** |
| scripts.head brand overlay | true | false | **PASS** |

Live GET po dryRun: původní version beze změny.

## Wave 1 (při „nasadit“)

1. GET `design` + `scripts` (aktuální version)
2. PATCH design (`wave1/design.patch.json`) — ostré
3. PATCH scripts.head (`wave1/scripts.head.html`) — ostré
4. Smoke: homepage, `/zarizeni/`, detail produktu, rezervace CTA

## Wave 2 (později, není v „nasadit“)

- SYS-2 / SYS-3 karty
- Homepage copy / hero search widget
- Header menu úpravy

## Po „nasadit“ ručně zkontrolovat

- [ ] Tlačítka blue / hover pink
- [ ] Open Sans
- [ ] WhatsApp FAB
- [ ] CTA „Vyberte zařízení“
- [ ] Rezervace na detailu produktu funguje
