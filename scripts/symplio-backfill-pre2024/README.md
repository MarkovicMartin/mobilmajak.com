# Backfill Symplio před rokem 2024 (automatický, insert-only)

## Co úloha dělá

- V **20:30** spustí na VPS doplnění chybějících prodejů **2017-10 až 2023-12** do `WEB_PRODEJE_ALL`.
- **Jen INSERT** – žádné `DELETE`, `UPDATE`, `ALTER`, přepis tabulky ani změna dat od **2024-01-01**.
- Měsíc, který už v DB má alespoň jeden řádek, se **přeskočí**.
- Při řádku s `Vystaveno >= 2024-01-01` v exportu import **okamžitě spadne** (ochrana produkce).
- Cron řádek se po startu **sám odstraní** (neběží zítra znovu).
- Běh pokračuje na pozadí (`nohup`); actor pro dnešek (cron každé 2 min) se **nevypíná** – historie se netýká dneška.

## Před spuštěním (preflight)

```bash
ssh -i .ssh/webmajak_vps/mobilmajak_vps_ed25519 root@194.182.87.138 \
  bash /opt/actor/ACTOR_FINALL_WEB_PRODEJE_ALL/test-backfill-pre2024-preflight.sh
```

Kontroluje: soubory, MySQL (`connectToMySQL` + `.env.db`), lock, že před 2024 ještě nejsou data.

## Nasazení + cron na večer

```bash
chmod +x scripts/symplio-backfill-pre2024/deploy-and-schedule.sh
./scripts/symplio-backfill-pre2024/deploy-and-schedule.sh          # dnes 20:30
./scripts/symplio-backfill-pre2024/deploy-and-schedule.sh today 21:00
```

Nahraje skripty, `backend/.env` → VPS `.env.db` (chmod 600), spustí preflight, nastaví jednorázový cron.

## Sledování

```bash
ssh -i .ssh/webmajak_vps/mobilmajak_vps_ed25519 root@194.182.87.138 \
  tail -f /opt/actor/ACTOR_FINALL_WEB_PRODEJE_ALL/reports/backfill_pre2024_scheduled.log
```

## Ruční test jednoho měsíce (na VPS)

```bash
cd /opt/actor/ACTOR_FINALL_WEB_PRODEJE_ALL
node backfill-pre2024-insert-only.js --from 2017-10-01 --to 2017-10-31 --download
```

## Odhad délky

~75 měsíců × stažení Symplio + import – typicky **několik hodin přes noc**, ne jedna minuta.
