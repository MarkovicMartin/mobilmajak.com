import { formatISODate } from '../../../utils/analyticsDateRange';

export const CHART_PRESETS = [
    { id: 'month', label: 'Tento měsíc', defaultCompare: 'prev_month' },
    { id: 'quarter', label: 'Kvartál', defaultCompare: 'prev_quarter' },
    { id: 'year', label: 'Rok', defaultCompare: 'prev_year' },
];

export const COMPARE_OPTIONS = [
    { id: 'prev_month', label: 'vs předchozí měsíc' },
    { id: 'prev_quarter', label: 'vs předchozí kvartál' },
    { id: 'prev_year', label: 'vs předchozí rok' },
];

/** Rozsah grafu nezávislý na filtrech tabulky (měsíční body). */
export const buildPolozkyChartRange = (presetId) => {
    const now = new Date();
    const today = formatISODate(now);

    if (presetId === 'year') {
        return {
            start_date: formatISODate(new Date(now.getFullYear(), 0, 1)),
            end_date: today,
        };
    }
    if (presetId === 'quarter') {
        const q = Math.floor(now.getMonth() / 3);
        const qStart = new Date(now.getFullYear(), q * 3, 1);
        const qEnd = new Date(now.getFullYear(), q * 3 + 3, 0);
        return {
            start_date: formatISODate(qStart),
            end_date: qEnd > now ? today : formatISODate(qEnd),
        };
    }
    return {
        start_date: formatISODate(new Date(now.getFullYear(), now.getMonth() - 11, 1)),
        end_date: today,
    };
};

export const defaultCompareForPreset = (presetId) =>
    CHART_PRESETS.find((p) => p.id === presetId)?.defaultCompare || 'prev_year';

export const TIMELINE_METRIC_KEYS = new Set([
    'polozky_nad_100',
    'sluzby_celkem',
    'sunshine',
    'unikatni_doklady',
    'celkovy_obrat',
    'ct300',
    'ct600',
    'ct1200',
    'akt',
    'zah250',
    'nap',
    'zah500',
    'kop250',
    'kop500',
    'pz1',
    'knz',
    'sklicka',
    'lepeni',
    'vykupy',
    'NOVE_TELEFONY',
    'BAZAROVE_TELEFONY',
    'PRISLUSENSTVI_SKLA',
    'PRISLUSENSTVI_OBALY',
    'SLUZBY',
    'SERVIS',
]);

export const pickChartMetric = (visibleMetrics) => {
    if (!visibleMetrics?.size) return 'polozky_nad_100';
    for (const key of visibleMetrics) {
        if (TIMELINE_METRIC_KEYS.has(key)) return key;
    }
    return 'polozky_nad_100';
};
