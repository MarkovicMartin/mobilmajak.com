# Veřejné ceníky v MyRepair

Manuál pro zaměstnance. Ceny na webu [servismajak.cz](https://servismajak.cz) se berou z karet služeb v MyRepair. Samostatný ceník na webu není.

Veřejná částka je pole **Částka s DPH** v bloku **Ceník**. U výměny displeje iPhone 7 je to 1 700 Kč a stejná částka je na stránce služby jako „Konečná cena včetně dílu a práce“.

Cena je společná pro všechny pobočky. Čas opravy může mít pobočka vlastní.

## Přihlášení

1. Otevřete [workspace.myrepair.app](https://workspace.myrepair.app/).
2. Vyberte svou pobočku.
3. V levém menu otevřete **Produkty a sklady → Přehled**.

Na úvodní obrazovce přehledu zvolte kategorii, například **Mobilní telefony**. Bez kategorie se služby nezobrazí.

## Změna jedné ceny

1. V levém stromu dojděte na zařízení, například Mobilní telefony → Apple → iPhone 7.
2. Do filtru **Název produktu** napište část názvu, třeba `displej`, a potvrďte hledání.
3. V řádku služby upravte částku ve sloupci **Cena**. Nechte **Konečná cena**, pokud má zákazník vidět pevnou cenu. **Cena od** použijte jen tehdy, když se má na webu ukázat „od“.
4. Klikněte na **Uložit změny**.

Stejná částka je v detailu. Řádek otevřete odkazem **Edit** nebo kliknutím na název. Detail je na adrese `product/detail/?pid=…`.

V detailu:

1. Najděte blok **Ceník → Cena pro zákazníka**. Text v aplikaci: „Tohle je částka a text, které se ukazují zákazníkovi.“
2. Do **Částka s DPH** napište novou cenu v korunách včetně DPH. Desetinnou čárku i tečku systém bere.
3. **Režim DPH** nechte 21 %, pokud nejde o jinou sazbu.
4. Klikněte na **Uložit změny**.

## Co které pole dělá

| Pole | Význam |
| --- | --- |
| Částka s DPH | Cena na webu, v rezervaci a při novém přidání položky do zakázky |
| Zobrazení | **Cena** = pevná částka. **Od** = na webu se ukáže „od“ |
| Jednotka | `/ks`, `/sada` nebo `/službu`. U oprav nechávejte `/ks` |
| Text pod cenou | Věta pod cenou. U oprav je „Konečná cena včetně dílu a práce“ |
| Více kusů | Zákazník si na webu sám mění počet. U oprav nechávejte vypnuté |
| Výchozí čas na opravu | Minuty na webu. `0` se na webu tváří jako oprava na počkání |
| Čas na opravu podle pobočky | Prázdné pole převezme výchozí čas. Vyplněné platí jen pro tu pobočku |
| Viditelnost | **Veřejně viditelné** je na webu. **Viditelné jen pro správce** a **Skryté** na webu nejsou |
| Druh produktu | Veřejný ceník oprav jsou položky **Služba**. **Součástka** je díl na sklad |
| Nákupní cena | Interní náklad. Na webu se neukazuje a při změně ceníku se nemění |
| Prodejní cena bez DPH, marže, přirážka | Dopočet z částky s DPH a nákupní ceny |

Název na webu je **Název produktu**. **Doplněk k názvu** je druhý řádek, například „Servis na iPhone 7“. **URL** neměňte, jinak přestane fungovat starý odkaz.

## Hromadná změna

1. Ve přehledu zaškrtněte služby. **Vybrat vše ve výsledcích** vezme celý aktuální filtr, nejen jednu stránku.
2. Otevřete **Hromadná akce → Změnit ceny**.
3. Zvolte typ **Procenta (%)** nebo **Pevná částka (Kč)**, směr **Zvýšit** nebo **Snížit** a hodnotu.
4. Klikněte na **Simulovat změnu** a zkontrolujte sloupce Původní cena, Nová cena a Rozdíl.
5. Teprve potom **Použít změnu**.

Náhled ukáže nejvýše pět položek. Při „vybrat vše“ je to prvních pět z filtru, změna se ale uloží na celý výběr.

**Zviditelnit** a **Skrýt** ve stejné nabídce přepnou viditelnost na webu.

## Schování služby z webu

V detailu v bloku **Pokročilé** nastavte **Viditelnost** na **Skryté** nebo **Viditelné jen pro správce** a uložte. Služba zmizí z [servismajak.cz](https://servismajak.cz). V administraci ji dál najdete.

## Kontrola

1. Na webu otevřete zařízení, například [servismajak.cz/zarizeni/iphone-7](https://servismajak.cz/zarizeni/iphone-7), nebo přímo stránku služby.
2. Obnovte stránku. Má tam být nová **Částka s DPH** a text pod cenou.
3. V přehledu MyRepair je u řádku i **Náhled**.

Když částka nesedí, je uložená jiná karta se stejným názvem, nebo je **Zobrazení** přepnuté na **Od**.

## Na co dát pozor

- Cenu měňte v **Částka s DPH**. Nákupní cenu nechte být.
- Nová cena platí pro web a pro položku přidanou do zakázky až po uložení. Už vloženou položku v rozpracované zakázce karta sama nepřepíše.
- Neměňte **URL** ani **Druh produktu**.
- Hromadnou změnu nejdřív simulujte. Špatný filtr přepíše i služby, které jste nechtěli.
- Čas opravy `0` na webu znamená „na počkání“. Když má oprava trvat, vyplňte minuty.
