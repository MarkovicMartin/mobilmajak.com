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

Pořadí importů je v `ui.css` (tokeny → design-system → legacy → dark → components → modály).

## Změna vzhledu

1. Barvy / tmavý režim → uprav `theme.css` (`:root` a `.dark-mode`).
2. Všechny inputy/selecty/textarea → už řeší `components.css` (`.App …`).
3. Nový modul → vlastní CSS jen pro layout (grid, šířky); barvy přes `var(--bg-card)` atd.
4. Modál → layout v modulu, shell v `Modals.css`.

## Dock / obsah pod hlavičkou

`DockNavbar.js` nastavuje `--dock-clearance` na `<html>`. Nepřepisovat v `.dark-mode` na menší hodnotu.
