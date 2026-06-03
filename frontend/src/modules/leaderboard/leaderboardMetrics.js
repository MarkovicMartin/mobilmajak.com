import { VICEPRACE_LABEL, formatVicepraceObrat } from '../../constants/viceprace';

export const METRIC_KEYS = {
    TOTAL_POINTS: 'total_points',
    SERVIS: 'servis',
    VYKUPY: 'vykupy',
    VICEPRACE: 'viceprace',
    PRUMER_POLOZEK: 'prumer_polozek',
    PRUMER_HODNOTA: 'prumer_hodnota',
    LAST_PERIOD: 'last_period',
};

export const METRICS = {
    [METRIC_KEYS.TOTAL_POINTS]: {
        sortKey: 'total_points',
        label: 'Celkové body',
        scoreLabel: 'BODŮ',
        rankSubtitle: 'bodového hodnocení',
    },
    [METRIC_KEYS.SERVIS]: {
        sortKey: 'servis_provize',
        label: 'Servis',
        scoreLabel: 'BODŮ',
        rankSubtitle: 'servisní provize z marže',
    },
    [METRIC_KEYS.VYKUPY]: {
        sortKey: 'vykupy',
        label: 'Výkupy',
        scoreLabel: 'KS',
        rankSubtitle: 'počtu výkupů (50 b./kus)',
    },
    [METRIC_KEYS.VICEPRACE]: {
        sortKey: 'viceprace_obrat',
        label: VICEPRACE_LABEL,
        scoreLabel: 'OBRAT',
        rankSubtitle: VICEPRACE_LABEL.toLowerCase(),
    },
    [METRIC_KEYS.PRUMER_POLOZEK]: {
        sortKey: 'prumer_polozek_uctu',
        label: 'Průměr pol./účt.',
        scoreLabel: 'PRŮMĚR',
        rankSubtitle: 'průměru položek na účtenku',
    },
    [METRIC_KEYS.PRUMER_HODNOTA]: {
        sortKey: 'prumer_hodnota_uctenky',
        label: 'Prům. hodnota účt.',
        scoreLabel: 'PRŮMĚR',
        rankSubtitle: 'průměrné hodnoty účtenky',
    },
    [METRIC_KEYS.LAST_PERIOD]: {
        sortKey: null,
        label: 'Minulý měsíc',
        labelDay: 'Minulá směna',
        scoreLabel: 'BODŮ',
        rankSubtitle: 'skóre z minulého měsíce',
        rankSubtitleDay: 'bodů z minulé směny',
    },
};

export const getLastPeriodValue = (seller, isDay) =>
    isDay ? (seller.last_shift_points || 0) : (seller.last_month_points || 0);

const OPPOSITE_METRIC = {
    [METRIC_KEYS.PRUMER_POLOZEK]: METRIC_KEYS.PRUMER_HODNOTA,
    [METRIC_KEYS.PRUMER_HODNOTA]: METRIC_KEYS.PRUMER_POLOZEK,
};

export const formatPrumerHodnotaUctenky = (value) => {
    const n = Number(value);
    if (!Number.isFinite(n) || n <= 0) return '—';
    return new Intl.NumberFormat('cs-CZ', {
        style: 'currency',
        currency: 'CZK',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
    }).format(Math.round(n));
};

export const getMetricNumericValue = (seller, metricKey, isDay = false) => {
    if (metricKey === METRIC_KEYS.LAST_PERIOD) {
        return getLastPeriodValue(seller, isDay);
    }
    const cfg = METRICS[metricKey];
    if (!cfg?.sortKey) return 0;
    const raw = seller[cfg.sortKey];
    const n = Number(raw);
    return Number.isFinite(n) ? n : 0;
};

export const formatMetricValue = (seller, metricKey, isDay = false) => {
    switch (metricKey) {
        case METRIC_KEYS.VICEPRACE:
            return formatVicepraceObrat(seller.viceprace_obrat);
        case METRIC_KEYS.PRUMER_POLOZEK:
            return (seller.prumer_polozek_uctu ?? 0).toFixed(2);
        case METRIC_KEYS.PRUMER_HODNOTA:
            return formatPrumerHodnotaUctenky(seller.prumer_hodnota_uctenky);
        case METRIC_KEYS.LAST_PERIOD:
        case METRIC_KEYS.TOTAL_POINTS:
        default:
            return getMetricNumericValue(seller, metricKey, isDay).toLocaleString('cs-CZ');
    }
};

export const sortByMetric = (data, metricKey, isDay = false) => {
    const sorted = [...data].sort(
        (a, b) => getMetricNumericValue(b, metricKey, isDay) - getMetricNumericValue(a, metricKey, isDay),
    );
    return sorted.map((seller, index) => ({
        ...seller,
        position: index + 1,
    }));
};

export const getOppositeMetric = (metricKey) => OPPOSITE_METRIC[metricKey] || null;

export const isExpandableMetric = (metricKey) =>
    metricKey === METRIC_KEYS.TOTAL_POINTS
    || metricKey === METRIC_KEYS.PRUMER_POLOZEK
    || metricKey === METRIC_KEYS.PRUMER_HODNOTA;

/** Nejlepší řádek podle metriky (pro stat karty). */
export const getTopByMetric = (data, metricKey, isDay = false) => {
    if (!data?.length) {
        return { value: 0, name: '—', row: null };
    }
    const best = data.reduce((a, b) => (
        getMetricNumericValue(b, metricKey, isDay) > getMetricNumericValue(a, metricKey, isDay) ? b : a
    ));
    return {
        value: getMetricNumericValue(best, metricKey, isDay),
        name: best.prodejce || '—',
        row: best,
    };
};

export const STAT_CARD_META = {
    [METRIC_KEYS.TOTAL_POINTS]: { icon: '🏆', title: 'Celkové body', showSum: true },
    [METRIC_KEYS.SERVIS]: { icon: '🔧', title: 'Top servis' },
    [METRIC_KEYS.VYKUPY]: { icon: '📦', title: 'Top výkupy' },
    [METRIC_KEYS.VICEPRACE]: { icon: '🎁', title: null },
    [METRIC_KEYS.PRUMER_POLOZEK]: { icon: '📊', title: 'Top pol./účt.' },
    [METRIC_KEYS.PRUMER_HODNOTA]: { icon: '💰', title: 'Top hodn. účt.' },
    [METRIC_KEYS.LAST_PERIOD]: {
        icon: '🎯',
        titleMonth: 'Nejlepší skóre minulý měsíc',
        titleDay: 'Nejlepší výkon včera',
    },
};
