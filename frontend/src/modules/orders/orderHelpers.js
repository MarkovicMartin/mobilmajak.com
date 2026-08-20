/** Shared Orders status / MyRepair helpers */

export const MAIN_STATUS_COLUMNS = [
    { key: 'nove', label: 'Nové', color: '#ff9800', textColor: '#000' },
    { key: 'v_kosiku', label: 'v košíku', color: '#2196f3', textColor: '#fff' },
    { key: 'objednano', label: 'objednáno', color: '#ffeb3b', textColor: '#000' },
    { key: 'dorazilo_ceka', label: 'připraveno', color: '#4caf50', textColor: '#fff' },
    { key: 'hotovo', label: 'vyřízeno', color: '#9e9e9e', textColor: '#fff' },
];

export const ACTIVE_STATUS_COLUMNS = MAIN_STATUS_COLUMNS.filter((c) => c.key !== 'hotovo');
export const DONE_STATUS_COLUMN = MAIN_STATUS_COLUMNS.find((c) => c.key === 'hotovo');

export const MAIN_STATUS_KEYS = MAIN_STATUS_COLUMNS.map((c) => c.key);

export const FILTER_STATUS_OPTIONS = [
    { value: '', label: 'Všechny stavy' },
    ...MAIN_STATUS_COLUMNS.map((c) => ({ value: c.key, label: c.label })),
];

export const ALL_STATUS_OPTIONS = [
    ...MAIN_STATUS_COLUMNS.map((c) => ({
        value: c.key,
        label: c.label,
        color: c.color,
        textColor: c.textColor,
    })),
    { value: 'predobjednano', label: 'Předobjednáno', color: '#ffeb3b', textColor: '#000' },
];

export const STATUSES_REQUIRING_DODAVATEL = new Set(['v_kosiku', 'objednano']);

const NOT_YET_READY = new Set([
    'nove', 'v_kosiku', 'objednano', 'predobjednano', 'neni_skladem',
]);

/** Targets for "Přesunout do" in order detail (same as drag). */
export function getMoveTargets(currentStatus) {
    return {
        main: MAIN_STATUS_COLUMNS.filter((c) => c.key !== currentStatus),
        secondary: [],
    };
}

export function statusLabel(status) {
    return ALL_STATUS_OPTIONS.find((s) => s.value === status)?.label || status;
}

/**
 * Zvýraznění řádku:
 * - >5 dní od založení a stále ne připraveno/vyřízeno → červené
 * - v připraveno bez pohybu ≥3 dny → lehce červené
 * - v připraveno bez pohybu ≥7 dní → sytě červené
 */
export function orderAgeClass(order) {
    if (!order) return '';
    const status = order.status;
    const daysInStatus = typeof order.dni_ve_stavu === 'number' ? order.dni_ve_stavu : null;

    if (status === 'dorazilo_ceka') {
        if (daysInStatus != null && daysInStatus >= 7) return 'age-ready-severe';
        if (daysInStatus != null && daysInStatus >= 3) return 'age-ready-warn';
        return '';
    }

    if (status === 'hotovo' || status === 'storno') return '';

    if (NOT_YET_READY.has(status)) {
        const created = order.datum_vytvoreni ? new Date(order.datum_vytvoreni) : null;
        if (created && !Number.isNaN(created.getTime())) {
            const daysSinceCreate = Math.floor((Date.now() - created.getTime()) / 86400000);
            if (daysSinceCreate > 5) return 'age-pending';
        }
    }
    return '';
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

/** Prázdný telefon je OK; jinak min. 9 číslic, max 20 znaků vč. mezer, volitelná + předvolba. */
export function validateTelefonZakaznika(value) {
    const trimmed = (value || '').trim();
    if (!trimmed) return null;

    if (trimmed.length > 20) {
        return 'Telefon může mít nejvýše 20 znaků';
    }
    if (!/^\+?[0-9\s]+$/.test(trimmed)) {
        return 'Telefon smí obsahovat jen číslice, mezery a volitelně + na začátku';
    }
    const digits = trimmed.replace(/\D/g, '');
    if (digits.length < 9) {
        return 'Telefon musí mít alespoň 9 číslic';
    }
    return null;
}
