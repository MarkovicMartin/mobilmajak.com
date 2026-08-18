# Vallora booking API

Izolovaná Django app pro `api.vallora.cz` — proxy nad Lodgify Quote API.

## Endpointy

```
GET /search?arrival=YYYY-MM-DD&departure=YYYY-MM-DD&guests=2
GET /quote?propertyId=718797&arrival=YYYY-MM-DD&departure=YYYY-MM-DD&guests=2
GET /availability
```

Obsazený termín u `/quote` vrací `"available": false` (Lodgify code 666), ne 502.

Odpověď obsahuje `price.formatted` a `checkoutUrl` pro Lodgify checkout.

## Bezpečné nasazení (mobilmajak VPS)

**Nemění se** nginx vhost pro mobilmajak.com — pouze se přidá nový soubor pro `api.vallora.cz`.

1. `LODGIFY_API_KEY` do `/home/webmajak/webapp/backend/.env`
2. Deploy backendu (git pull + restart gunicorn)
3. Nový nginx vhost — viz `Vallora web 2/docs/deploy/nginx-api-vallora.conf`
4. `certbot --nginx -d api.vallora.cz`

## Test

```bash
export LODGIFY_API_KEY=...
python manage.py runserver 8001
curl "http://127.0.0.1:8001/quote?propertyId=718797&arrival=2026-09-01&departure=2026-09-05&guests=2"
```
