/**
 * Bodové sazby – shodné s backend analytics/points_config.py a sunshine_config.py
 * (u služeb příplatek nad základ 15 bodů/kus; SUNSHINE +15 bodů/kus navíc k položce nad 100 Kč).
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
    { key: 'vykupy', label: 'Výkupy', rate: 50 },
    { key: 'sunshine', label: 'Sunshine', rate: 15 },
];

/** CT300 / KNZ / LOS – pouze počet kusů (KNZ má body jen přes položky nad 100 Kč) */
export const CT300_INFO_KEY = 'ct300';
export const CT300_INFO_LABEL = 'CT300';
export const KNZ_INFO_KEY = 'knz';
export const KNZ_INFO_LABEL = 'KNZ';
export const LOS_INFO_KEY = 'lepeni';
export const LOS_INFO_LABEL = 'LOS';

export const INFO_ONLY_COMMISSIONS = [
    { key: CT300_INFO_KEY, label: CT300_INFO_LABEL },
    { key: KNZ_INFO_KEY, label: KNZ_INFO_LABEL },
    { key: LOS_INFO_KEY, label: LOS_INFO_LABEL },
];

export const SERVIS_BREAKDOWN_KEY = 'servis_marze';

export const BREAKDOWN_LINE_LABELS = {
    ...Object.fromEntries(PRODUCT_COMMISSIONS.map((p) => [p.key, p.label])),
    [CT300_INFO_KEY]: CT300_INFO_LABEL,
    [KNZ_INFO_KEY]: KNZ_INFO_LABEL,
    [LOS_INFO_KEY]: LOS_INFO_LABEL,
    [SERVIS_BREAKDOWN_KEY]: 'Servis (marže)',
    vykupy: 'Výkupy',
};
