/** Shared Orders status / MyRepair helpers */

export const MAIN_STATUS_COLUMNS = [
    { key: 'nove', label: 'Nové', color: '#ffeb3b', textColor: '#000' },
    { key: 'v_kosiku', label: 'v košíku', color: '#ff9800', textColor: '#000' },
    { key: 'objednano', label: 'objednáno', color: '#2196f3', textColor: '#fff' },
    { key: 'dorazilo_ceka', label: 'připraveno', color: '#4caf50', textColor: '#fff' },
    { key: 'hotovo', label: 'vyřízeno', color: '#8bc34a', textColor: '#000' },
];

export const MAIN_STATUS_KEYS = MAIN_STATUS_COLUMNS.map((c) => c.key);

export const FILTER_STATUS_OPTIONS = [
    { value: '', label: 'Hlavní stavy' },
    ...MAIN_STATUS_COLUMNS.map((c) => ({ value: c.key, label: c.label })),
    { value: 'neni_skladem', label: 'Není skladem' },
    { value: 'storno', label: 'Storno' },
    { value: 'predobjednano', label: 'Předobjednáno (legacy)' },
];

export const SECONDARY_STATUS_OPTIONS = [
    { value: 'neni_skladem', label: 'Není skladem', color: '#f44336', textColor: '#fff' },
    { value: 'storno', label: 'Storno', color: '#757575', textColor: '#fff' },
];

export const ALL_STATUS_OPTIONS = [
    ...MAIN_STATUS_COLUMNS.map((c) => ({
        value: c.key,
        label: c.label,
        color: c.color,
        textColor: c.textColor,
    })),
    ...SECONDARY_STATUS_OPTIONS,
    { value: 'predobjednano', label: 'Předobjednáno', color: '#9c27b0', textColor: '#fff' },
];

export const STATUSES_REQUIRING_DODAVATEL = new Set(['v_kosiku', 'objednano']);

/** Targets for "Přesunout do" in order detail (same rules as drag + secondary). */
export function getMoveTargets(currentStatus) {
    return {
        main: MAIN_STATUS_COLUMNS.filter((c) => c.key !== currentStatus),
        secondary: SECONDARY_STATUS_OPTIONS.filter((s) => s.value !== currentStatus),
    };
}

export function statusLabel(status) {
    return ALL_STATUS_OPTIONS.find((s) => s.value === status)?.label || status;
}

const MYREPAIR_SEARCH_BASE =
    'https://workspace.myrepair.app/calendar/search.php?query=';

export function myrepairUrl(servisniCislo) {
    const q = (servisniCislo || '').trim();
    if (!q) return null;
    return `${MYREPAIR_SEARCH_BASE}${encodeURIComponent(q)}`;
}

export function formatOrderDate(dateString) {
    if (!dateString) return '';
    const date = new Date(dateString);
    const d = date.getDate();
    const m = date.getMonth() + 1;
    return `${d}.${m}.`;
}

export function formatZadal(user) {
    if (!user) return '—';
    const last = (user.prijmeni || '').trim();
    if (last) return last;
    return (user.jmeno || '').trim() || '—';
}

export function formatProdejna(prodejna) {
    if (!prodejna) return '—';
    return prodejna.nazev_kratkiy || prodejna.nazev || '—';
}
