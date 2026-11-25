# Nasazení wave 1 — stačí říct „nasadit“

Agent po příkazu **nasadit** / **deploy** provede **jen wave 1** (barvy + CSS overlay). Live data a rezervace zůstávají MyRepair.

## Postup (automaticky)

1. GET `design` a `scripts` → aktuální `version`
2. PATCH `design` z `wave1/design.patch.json` (**bez** dryRun)
3. PATCH `scripts` head z `wave1/scripts.head.html` (**bez** dryRun), zachovat stávající WhatsApp + CTA JS
4. Ověřit GET (nové version) + smoke URL:
   - https://servismajak.cz/
   - https://servismajak.cz/zarizeni/
   - https://servismajak.cz/apple-iphone-13-vymena-displeje
5. Aktualizovat `STATUS.md`

## Rollback

1. GET aktuální version
2. PATCH `data` z `backup/design.json` a `backup/scripts.json`
3. Smoke homepage

## Co wave 1 NEDĚLÁ

- nepřenáší celý preview SPA
- nemění SYS-2/3 šablony
- nemění homepage HTML bloky
- nepřidává hero finder / top-search suggest (to je wave 2)
