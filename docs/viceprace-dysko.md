# Vícepráce (P63615) a žebříček dýškařů

## Identifikace

- Symplio kód položky: **P63615**
- Konfigurace: `backend/analytics/viceprace_config.py`, `frontend/src/constants/viceprace.js`

## Pravidla

| Metrika | Počítá se? |
|---------|------------|
| Položky nad 100 Kč (`polozky_nad_100`) | **Ne** – P63615 je vyloučen i při ceně ≥ 100 Kč |
| 15 bodů / kus | **Ne** |
| Celkové body žebříčku | **Ne** (servis a produkty beze změny) |
| `viceprace_obrat` | **Ano** – součet obratu za P63615: **`Pocet_kusu × Cena_ks_vcl_DPH`** (Kč s DPH) |

## Kde se zobrazuje

- **Profil** – metrika + řádek „Vícepráce: X Kč (0 bodů)“
- **Analytika → Prodejny-Položky** – karta Nejlepší dýškař, detail u prodejce
- **Žebříček bodů** – karta „Top dýškař“ (počet ks), sloupec Vícepráce u TOP 3 a v tabulce

## API pole

- `viceprace_obrat` – na řádcích prodejce (Kč)
- `meta.viceprace_leader` – `{ id, prodejce, obrat }` u žebříčku
