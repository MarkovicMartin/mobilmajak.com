---
name: uprava-karet
description: >-
  Upravuje karty zboží ve Sympliu (mobilmajak.cz/admin) podle manuálu
  Zakládání karet a podle cen už založených karet. Použij při žádosti o úpravu
  karet, založení karty, doplnění názvu, popisu, ceny, fotky nebo přesun
  Ke zpracování / Ke kontrole / Nezaloženo.
---

# Automatizované úpravy karet

Zápis jde do Symplia na `https://www.mobilmajak.cz/admin`. MyRepair se pro karty zboží nepoužívá.

Názvy, fotky, popisy a fronta jsou z dokumentu „Zakládání karet nového zboží“. Karta má dvě ceny: prodejní na pokladně a nižší e-shopovou. Ceny z Bible nepoužívej. Obě ber ze sourozence stejné řady, nebo z tabulky níže.

Před zápisem ukaž návrh polí a počkej na potvrzení dávky.

## Fronta

Katalog → Zakládání → složka prodejny (Globus, Šternberk, Senimo, Zlín, Přerov, Vsetín):

1. **Ke zpracování** — týdenní dávka. Doplň a přepiš kartu, pak ji přesuň do Ke kontrole.
2. **Ke kontrole** — hotové karty. Do e-shopu je přesouvá administrátor, automat ne.
3. **Nezaloženo** — chybí fotka, popis nebo se nedá určit řada a cena. Uveď důvod.

Hlavní kategorie (puntík) karty ve frontě je **Ke kontrole** dané prodejny. K tomu přidej e-shopové listy z části Kategorie. Nehodící kategorie odstraň. Do e-shopu jako hlavní kategorii kartu nepřesouvej, to dělá administrátor.

Samostatný strom **Automatizace zakládání** má **K založení** a **Ke kontrole**. Ten není týdenní fronta prodejny.

## Pole karty

1. **Název** — šablona níže. Dodavatelský název v angličtině převeď na šablonu.
2. **Výrobce** — stejný jako u existující karty stejné řady (Tactical, Fixed, Swissten, OBAL:ME, MobilMajak, Forcell, Roar, OEM, PARTNER PL, MG). Forcell a Roar nech. `MG` jen když stejná řada už `MG` má, nebo značka v manuálu spadá pod zkratku a sourozenec neexistuje.
3. **Dodavatel** — jen u složky, která je ve zpracování. Teď je to Katalog / !Import / PARTNER PL (201): prázdné pole Dodavatel nastav na PARTNER PL (`CZbozi.dodavatel_id` 2). Vyplněného jiného dodavatele nepřepisuj. Výrobce tím neměň. Další složky se doplní, až budou zadané.
4. **Ceny** — prodejní (pokladna) a e-shopová. E-shop je u příslušenství obvykle kolem poloviny pokladny, dopočet polovinou nepoužívej. Obě vezmi z tabulky nebo ze sourozence.
5. **Váha** — ze sourozence stejné řady. Když není: kryt a knížka 100 g, sklo a fólie 50 g. Tactical a část DUX DUCIS má 50 g, sourozenec má přednost.
6. **Obrázky** — jen z webu dodavatele, bílé pozadí, přesně ten výrobek. U krytu a knížky musí výřez kamery sedět na daný model. Ilustrační foto je důvod pro Nezaloženo.
7. **Krátký popis** — první věty popisu. Kryty, knížky a skla: text z webu dodavatele. Cizí jazyk přelož.
8. **Popis** — věty z krátkého popisu a pak celý text.
9. **Parametry** — jen u telefonů (gsmarena.com, případně Alza nebo CZC). U pouzdra a krytu jen BARVA a TYP.

## Ceny

Na kartě vyplň obě. Prodejní je ta, kterou bere pokladna. E-shopová je nižší cena na webu.

Nejdřív sourozenec: nejnovější aktivní karta stejné řady mimo Ke zpracování. Řada je text typu za pomlčkou (Frame Circle, Silicone, Tender Book, 5D, 9H, sklo kamery). Z ní opiš obě ceny. iPhone a ostatní mají u těchto řad stejnou pokladní cenu.

Když sourozenec není, použij tabulku. Je z účtenek roku 2026 (nejčastější cena s DPH; druhá vlna 319 a 479 je sleva na pokladně, ne jiný ceník) a z e-shopových objednávek. Částky jsou v Kč.

| Řada | Pokladna | E-shop |
| --- | --- | --- |
| knížkové Tender Book, Luna Book | 449 | 199 |
| Frame Circle, Mag Cover, Electro Mag, Mag Aurora | 399 | 199 |
| Silicone, Matt, Carbon | 349 | 149 |
| Tactical, MagForce | 349 | 299 |
| DUX DUCIS | 349 | podle sourozence, 249 nebo 399 |
| sklo 9H | 399 | 149 |
| sklo 5D / 6D | 599 | 199 |
| Mr.Monkey | 599 | 299 |
| Flexible / Nano | 399 | 199 |
| sklo kamery | 299 | 149 |

Sklo bez řady v názvu je 9H. 5D a 6D jsou v názvu uvedeny. Zadní kryt, který v tabulce nemá vlastní řadu (K-Look, Smoke Hybrid a další MagSafe kryty), má cenu Mag Cover: pokladna 399, e-shop 199.

Řada v tabulce není, sourozenec chybí a nejde ani o sklo ani o zadní kryt: obě ceny nech prázdné, kartu nech v K založení a zapiš nedostatek `nezname_ceny`. Polovinu pokladny jako e-shop nedoplňuj.

## Názvy

| Druh | Tvar | Příklad |
| --- | --- | --- |
| Zadní kryt | `Obal / kryt na ZNAČKA MODEL BARVA - TYP` | Obal / kryt na Apple iPhone 17 černý - Variete Mag Cover |
| Knížkové pouzdro | `Pouzdro / obal na ZNAČKA MODEL BARVA - knížkové TYP` | Pouzdro / obal na Apple iPhone 17 černé - knížkové Tender |
| Sklo displeje | `Tvrzené / ochranné sklo ZNAČKA MODEL BARVA - OZNAČENÍ` | Tvrzené / ochranné sklo Apple iPhone 16 Pro / 17 černé - 6D Pro Veason Glass |
| Sklo kamery | `Tvrzené / ochranné sklo kamery ZNAČKA MODEL - OZNAČENÍ` | Tvrzené / ochranné sklo kamery Apple iPhone 17 - 5D Full Glue |

Barvu vynech, jen když ji výrobek nemá. Více modelů spojuj ` / `.

Popisy skel, když dodavatel žádný nedá:

- Ceramic Glass: měkčí, kryje celý displej, lepí po celé ploše, proti světlu dělá malé mapy.
- 9H: tvrdé, kryje zobrazovací část, není až do krajů, lepí po celé ploše.
- 5D: černý rámeček, celá plocha, lepí po celé ploše.
- Flexible / Nano: fólie, téměř celá plocha.

## Kategorie

E-shopový list je nejhlubší existující kategorie modelu. Složku značky ber tak, jak už ve stromu je (APPLE, SAMSUNG, XIAOMI, Honor). Novou kategorii nezakládej. Když list modelu není a žádný vhodný list neexistuje, kartu nech v K založení a zapiš nedostatek `chybejici_kategorie`. Když název uvádí víc modelů a aspoň jeden list existuje, zařaď do existujících listů, přesuň kartu do Ke kontrole a chybějící list zapiš stejně.

| Zboží | Cesta |
| --- | --- |
| kryt i knížkové pouzdro | PŘÍSLUŠENSTVÍ → Pouzdra a kryty → ZNAČKA → řada → model |
| sklo displeje i sklo kamery | PŘÍSLUŠENSTVÍ → Skla a fólie → ZNAČKA → model |

Apple u pouzder: řada `iPhone 17`, list `iPhone 17 Pro` / `iPhone 17 Pro Max` / `iPhone 17` / `iPhone Air` / `iPhone 17e`. U skel je model rovnou list (`iPhone 17 Pro`), bez páté úrovně. Samsung: řada `Galaxy A` nebo `Galaxy S`, list `Galaxy A27`, `Galaxy S25`. Xiaomi Redmi Note: řada `Xiaomi Redmi Note`, list `Xiaomi Redmi Note 15 Pro`.

Název s více modely (`iPhone 17 Pro / 18 Pro`): přidej list každého modelu. Puntík zůstává na Ke kontrole.

## Nové telefony

Příslušenství a telefon se zakládají jinak. Nový telefon nepatří do PŘÍSLUŠENSTVÍ ani do POUŽITÉ TELEFONY. Ceník příslušenství (polovina na e-shopu) se na telefon nepoužívá. Pokladna i e-shop mají stejnou cenu.

Jedna karta = jedna barva a jedna paměť. Název opisuj ze sourozence stejného modelu. Když není, tvar je `Značka Model kapacita/RAM barva`, například `Xiaomi Redmi Note 17 256+6GB Black` nebo `Samsung Galaxy A27 5G Black 256/8GB`. Výrobce je skutečná značka. IMEI na kartu nepatří, patří do poznámky příjemky.

Cenu ber z karty stejného modelu a paměti. Když taková není, cenu nech prázdnou. Váha je skutečná hmotnost v gramech, stejné číslo jde do parametru Hmotnost.

Kategorie: **NOVÉ TELEFONY → značka → řada → model**. Tlačítková Nokia jde pod `Nokia → Tlačítkové → Nokia 210`. List nezakládej. Když model ve stromu není, nech kartu v K založení a zapiš nedostatek `chybejici_kategorie`.

Parametry ber z gsmarena.com a vyplň jen ty, které už na kartách jsou: Barva (česky), Operační paměť RAM, Velikost vnitřního úložiště, Počet SIM, Operační systém, Verze operačního systému, Velikost displeje, Rozlišení displeje, Typ displeje, Kapacita baterie, Hmotnost, Výška, Šířka, Hloubka, Frekvence procesoru, Počet jader procesoru, Rozlišení zadního fotoaparátu, Počet objektivů zadního fotoaparátu, Vlastnosti zadního fotoaparátu, Rozlišení předního fotoaparátu, Nabíjecí konektor, Audio jack, Rozšíření vnitřního úložiště, Maximální kapacita pro rozšíření úložiště, Funkce. Nový název parametru nezakládej. Karta bez těchto parametrů není hotová, i když ji tak někdo uložil.

## Kontrola před přesunem

Karta smí do Ke kontrole, jen když sedí název, výrobce, dodavatel dané složky, obě ceny, váha, vlastní fotka, oba popisy a kategorie. U telefonu navíc parametry a jedna karta na barvu a paměť. Hlavní kategorie je Ke kontrole prodejny.

Výstup dávky: u každé karty odkaz do Symplia, nový název, prodejní cena, e-shopová cena, odkud ceny jsou, e-shopové listy, nebo důvod Nezaloženo / ponecháno ve frontě.

## Týdenní běh

Jednou týdně, v sobotu večer po zavření prodejen, projdi jen **Katalog / !Import / PARTNER PL** (kategorie 201) a jen karty skladem. Ostatní složky a karty bez skladu nech. U karty skladem nastav prázdného dodavatele na PARTNER PL a dál použij postup v tomto souboru. Hotovou kartu přesuň do Ke kontrole (15563): puntík tam, e-shopové listy přidané. Do e-shopu jako hlavní kategorii kartu nepřesouvej.

Přihlášení do Symplia běží na serveru stejným Chrome jako noční importy. Fotku z webu dodavatele, volný popis a kartu, u které řada nebo list není jistý, automat nedoplňuje a kartu ve složce nechá.

Takový problém zapiš do Kategorie zboží → Automatizace karet, ne do chatu:

```
./scripts/backend-run.sh manage.py automatizace_karet --kod P… --typ chybejici_fotka --zbozi-id … --nazev "…" --text "…"
```

Starší fronta zakládání zapisuje do stejné záložky:

```
./scripts/backend-run.sh manage.py zakladani_nedostatek --kod P… --typ chybejici_kategorie --zbozi-id … --nazev "…" --text "…"
```

Typy: `chybejici_kategorie`, `nezname_ceny`, `chybejici_fotka`, `nejasna_rada`, `jine`. Stejný otevřený kód a typ se nepřidává znovu, doplní se text. Cron ani deploy se nespouští, dokud dávka neprojde kontrolou.
