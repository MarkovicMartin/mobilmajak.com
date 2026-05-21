/**
 * Bodové sazby – shodné s backend analytics/points_config.py
 * (u služeb příplatek nad základ 15 bodů/kus u položek nad 100 Kč).
 */
export const PRODUCT_COMMISSIONS = [
    { key: 'polozky_nad_100', label: 'Položky nad 100 Kč', rate: 15 },
    { key: 'ct600', label: 'CT600', rate: 35 },
    { key: 'ct1200', label: 'CT1200', rate: 85 },
    { key: 'akt', label: 'AKT', rate: 15 },
    { key: 'zah250', label: 'ZAH250', rate: 15 },
    { key: 'nap', label: 'NAP', rate: 35 },
    { key: 'zah500', label: 'ZAH500', rate: 35 },
    { key: 'kop250', label: 'KOP250', rate: 15 },
    { key: 'kop500', label: 'KOP500', rate: 35 },
    { key: 'pz1', label: 'PZ1', rate: 85 },
    { key: 'knz', label: 'KNZ', rate: 15 },
];

/** CT300 – pouze počet kusů, nezapočítává se do bodů */
export const CT300_INFO_KEY = 'ct300';
export const CT300_INFO_LABEL = 'CT300';

export const SERVIS_BREAKDOWN_KEY = 'servis_marze';

export const BREAKDOWN_LINE_LABELS = {
    ...Object.fromEntries(PRODUCT_COMMISSIONS.map((p) => [p.key, p.label])),
    [CT300_INFO_KEY]: CT300_INFO_LABEL,
    [SERVIS_BREAKDOWN_KEY]: 'Servis (marže)',
};
