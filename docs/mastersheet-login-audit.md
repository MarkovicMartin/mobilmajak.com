# Audit přihlašovacích údajů – Mastersheet

Zdroj: `docs/mastersheet-prihlasovaci-loginy.json` (bez hesel).

Celkem záznamů: **395** | Unikátních loginů: **~155**

## Po prodejně (Mastersheet)

| Prodejna | Počet loginů |
|----------|--------------|
| Globus | 52 |
| Šternberk | 23 |
| Senimo | 27 |
| Čepkov | 27 |
| Přerov | 20 |
| Vsetín | 11 |
| Litovelská | 235 |

## Porovnání s modulem Přístupy

Spusťte s přístupem k DB:

    ./scripts/backend-run.sh manage.py audit_mastersheet_logins

Příkaz porovná (prodejna + služba + login) s tabulkou WEB_PRISTUPY_PRODEJNY.
Existující záznamy se **nemění**. Volitelně `--import-missing` přidá chybějící s heslem DOPLNIT_RUCNE.

Hesla zůstávají mimo git – doplnit ručně v modulu Přístupy.
