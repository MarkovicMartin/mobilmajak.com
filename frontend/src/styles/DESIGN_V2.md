# MOBIL MAJÁK – Design V2

Pravidla pro nový kód v rámci Web 2.0 obnovy. Legacy moduly se migrují postupně (Fáze 4).

## Tokeny

- Barvy, spacing, typografie, radius a z-index **pouze** z `theme.css`.
- Zakázané: inline `style={{ color: '#...' }}`, nové hex v modulovém CSS.
- Grafy: `--chart-1` … `--chart-5`, případně `chartTheme.js` (Fáze 5).

## Layout

- App shell: `AppShell` + třídy z `layout.css` (`.app-shell`, `.page`, `.page-header`, `.page-content`).
- Obsah: `max-width: var(--content-max-width)`, padding přes `--space-*`.
- Desktop: fixní sidebar (`--sidebar-width`). Mobil: top bar (`--header-height`) + drawer.

## Komponenty (Fáze 3+)

- Formuláře: `Select`, `DatePicker`, `DateRangePicker` – ne nativní `<select>` / `type="date"` v novém kódu.
- Navigace uvnitř modulu: `Tabs` / `SegmentControl`, ne vlastní tab lišty.
- Nadpisy: `PageHeader` – jeden hlavní nadpis na stránku.
- Modály: existující `Modal` + `primitives.css`.
- Tlačítka: `.btn`, `.btn--primary`, `.btn--secondary`, `.btn--ghost`.

## Navigace

- Jediný zdroj položek: `config/navigation.js`.
- Role: `adminOnly`, `managerOnly` (úkoly), `coachingOnly` (výkony).

## CSS

- Nové globální styly: `layout.css`, `primitives.css`, `forms-v2.css` (import v `ui.css` po `theme.css`).
- Modulové CSS: jen layout modulu; barvy z tokenů.
- Nepřidávat cross-importy mezi moduly a starým `DockNavbar`.

## Zakázané patterny v novém kódu

- Plovoucí dock navigace (`DockNavbar`, `--dock-clearance`).
- Duplicitní `NAV_ITEMS` mimo `navigation.js`.
- Emoji v produkčních nadpisech (výjimka: existující admin ikony do migrace).
