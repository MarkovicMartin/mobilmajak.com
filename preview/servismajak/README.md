# Servis Maják — half-live preview

Statický náhled nového vzhledu s **reálnými daty z MyRepair**.  
**Živý web `servismajak.cz` se nemění** — žádné zápisy do MyRepair website API.

## Co obsahuje

| Část | Zdroj |
|------|--------|
| Katalog (telefony / tablety / hodinky) | `data/devices.json` + `data/services-by-category.json` |
| Ceny oprav | export služeb MyRepair (5988) |
| Pobočky + otevírací doby | `data/locations.json` |
| Rady / blog | `data/pages.json` → odkaz na live |
| Hodnocení | 4,9 / 748 (`data/meta.json`) |
| Rezervace | odkaz na `https://servismajak.cz/zarizeni/…` |

## Spuštění lokálně

```bash
cd preview/servismajak
python3 -m http.server 8890
```

Otevřít: [http://127.0.0.1:8890/novy-navrh.html](http://127.0.0.1:8890/novy-navrh.html)

> Soubory musí běžet přes HTTP server (ne `file://`), jinak `fetch` nenačte JSON.

## Hlavní cesty

- Domů: `novy-navrh.html`
- Katalog: `katalog.html` → `?c=mobilni-telefony` → značka → model → opravy
- Hledání: `hledani-v2.html?q=iphone%2013%20displej`
- Pobočky: `pobocky-v2.html`
- Rady: `blog-v2.html`

## Obnova dat (jen čtení API)

Data jsou snapshot z MyRepair Private API (GET). Obnovení = znovu stáhnout kategorie / katalog / pobočky / pages do `data/`.  
Nikdy nevolat `update_website_*`, `PATCH` design/scripts/header.

## Export ZIP

Soubor vedle složky: `preview/servismajak-half-live.zip`
