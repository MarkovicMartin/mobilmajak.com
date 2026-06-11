# Styly frontendu

## Jediný import

V `App.js` stačí:

```js
import './styles/ui.css';
```

## Soubory

| Soubor | Účel |
|--------|------|
| `ui.css` | Vstupní bod – nic jiného neimportovat globálně |
| `theme.css` | **Tokeny** (`--brand-navy`, `--bg-input`, `--text-primary`, …) a `.dark-mode` |
| `components.css` | Globální formuláře a karty (načítá se jako poslední před modály) |
| `design-system.css` | Analytika, filtry, dlaždice |
| `dark-mode.css` | Přepisy modulů, které ještě mají staré hex |
| `legacy-brand.css` | Gradient tlačítka (submit, module-btn) |
| `Modals.css` | Overlay a scroll modálů |
| `ModuleSubnav.css` | Záložky modulu (analytika, plány, směny, výkony) – **nesmí** být `position: sticky` |
| `PeriodSegmentBar.css` | Segmentové přepínače období (žebříček, analytické presety) |
| `DateFilterBar.css` | Presety období + inline Od/Do jen v custom režimu |

Pořadí importů je v `ui.css` (tokeny → design-system → legacy → dark → components → subnav/segmenty → modály).

## Sdílené komponenty navigace a filtrů

| Komponenta | Soubor | Použití |
|------------|--------|---------|
| `ModuleSubnav` | `components/ModuleSubnav.js` | Záložky modulu (`NavLink` nebo tlačítka), volitelné `meta` vpravo |
| `PeriodSegmentBar` | `components/PeriodSegmentBar.js` | Rychlé volby období; aktivní segment se rozšíří |
| `DateFilterBar` | `components/DateFilterBar.js` | Analytika: presety + inline Od/Do pouze bez aktivního presetu |

Subnav scrolluje s obsahem – nepřipínat pod dock (`--subnav-sticky-top` zůstává v theme pro případné budoucí použití).

## Změna vzhledu

1. Barvy / tmavý režim → uprav `theme.css` (`:root` a `.dark-mode`).
2. Všechny inputy/selecty/textarea → už řeší `components.css` (`.App …`).
3. Nový modul → vlastní CSS jen pro layout (grid, šířky); barvy přes `var(--bg-card)` atd.
4. Modál → komponenta `components/Modal.js` + styly v `Modals.css`; vlastní CSS jen pro obsah (grid, tabulky).

## Dock / obsah pod hlavičkou

`DockNavbar.js` nastavuje `--dock-clearance` na `<html>`. Nepřepisovat v `.dark-mode` na menší hodnotu.
