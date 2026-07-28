import { REKLAMACE_STATUS, ZPUSOB_VYRIzeni_OPTIONS } from './constants';

export const STATUS_COLUMNS = [
    {
        key: REKLAMACE_STATUS.NEZPRACOVANE,
        label: 'Nezpracované',
        color: '#ffeb3b',
        textColor: '#000',
    },
    {
        key: REKLAMACE_STATUS.ODESLANE,
        label: 'Odeslané',
        color: '#ff9800',
        textColor: '#000',
    },
    {
        key: REKLAMACE_STATUS.VRIZENE,
        label: 'Vyřízené',
        color: '#8bc34a',
        textColor: '#000',
    },
];

export const STATUS_KEYS = STATUS_COLUMNS.map((c) => c.key);

export const FILTER_STATUS_OPTIONS = [
    { value: '', label: 'Všechny stavy' },
    ...STATUS_COLUMNS.map((c) => ({ value: c.key, label: c.label })),
];

/** Allowed forward transitions only (matches backend actions). */
export const ALLOWED_TRANSITIONS = {
    [REKLAMACE_STATUS.NEZPRACOVANE]: [REKLAMACE_STATUS.ODESLANE],
    [REKLAMACE_STATUS.ODESLANE]: [REKLAMACE_STATUS.VRIZENE],
    [REKLAMACE_STATUS.VRIZENE]: [],
};

export function getMoveTargets(currentStatus) {
    const allowed = ALLOWED_TRANSITIONS[currentStatus] || [];
    return STATUS_COLUMNS.filter((c) => allowed.includes(c.key));
}

export function canTransition(fromStatus, toStatus) {
    return (ALLOWED_TRANSITIONS[fromStatus] || []).includes(toStatus);
}

export function statusLabel(status) {
    return STATUS_COLUMNS.find((c) => c.key === status)?.label || status;
}

export function statusConfig(status) {
    return STATUS_COLUMNS.find((c) => c.key === status) || null;
}

export function groupByStatus(items) {
    const data = {};
    STATUS_COLUMNS.forEach((col) => {
        data[col.key] = {
            label: col.label,
            orders: [],
            count: 0,
        };
    });
    (items || []).forEach((item) => {
        const key = item.status in data ? item.status : REKLAMACE_STATUS.NEZPRACOVANE;
        data[key].orders.push(item);
        data[key].count = data[key].orders.length;
    });
    return data;
}

export function formatReklamaceDate(dateString) {
    if (!dateString) return '';
    const date = new Date(dateString);
    if (Number.isNaN(date.getTime())) return '';
    return `${date.getDate()}.${date.getMonth() + 1}.`;
}

export function formatDateTime(dateString) {
    if (!dateString) return '—';
    return new Date(dateString).toLocaleString('cs-CZ');
}

export function promptZpusobVyrizeni() {
    const labels = ZPUSOB_VYRIzeni_OPTIONS.map((o) => o.label).join(' / ');
    const entered = window.prompt(
        `Způsob vyřízení (${labels}). Zadejte: ${ZPUSOB_VYRIzeni_OPTIONS.map((o) => o.value).join(', ')}`,
        'vymena',
    );
    if (!entered || !entered.trim()) return null;
    const value = entered.trim().toLowerCase();
    const match = ZPUSOB_VYRIzeni_OPTIONS.find(
        (o) => o.value === value || o.label.toLowerCase() === value,
    );
    return match ? match.value : null;
}

export { ZPUSOB_VYRIzeni_OPTIONS, REKLAMACE_STATUS };
