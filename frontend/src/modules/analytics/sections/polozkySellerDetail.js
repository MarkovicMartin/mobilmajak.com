import { VICEPRACE_LABEL, formatVicepraceObrat } from '../../../constants/viceprace';

/** Všechny položky detailu prodejce – vždy zobrazené (i při 0). */
export const POLOZKY_SELLER_DETAIL_ITEMS = [
    {
        key: 'servis_provize',
        label: 'Servis',
        className: 'polozky-chip--servis',
        title: (item) => (item.servisni_prace != null
            ? '10 % marže servisních prací'
            : 'Uživatel nemá technik_id'),
        format: (item) => item.servis_provize ?? 0,
    },
    {
        key: 'viceprace_obrat',
        label: VICEPRACE_LABEL,
        className: 'polozky-chip--viceprace',
        title: 'Kód P63615, obrat s DPH',
        format: (item) => formatVicepraceObrat(item.viceprace_obrat),
    },
    { key: 'ct300', label: 'CT300', format: (item) => item.ct300 || 0 },
    { key: 'ct600', label: 'CT600', format: (item) => item.ct600 || 0 },
    { key: 'ct1200', label: 'CT1200', format: (item) => item.ct1200 || 0 },
    { key: 'akt', label: 'AKT', format: (item) => item.akt || 0 },
    { key: 'zah250', label: 'ZAH250', format: (item) => item.zah250 || 0 },
    { key: 'nap', label: 'NAP', format: (item) => item.nap || 0 },
    { key: 'zah500', label: 'ZAH500', format: (item) => item.zah500 || 0 },
    { key: 'kop250', label: 'KOP250', format: (item) => item.kop250 || 0 },
    { key: 'kop500', label: 'KOP500', format: (item) => item.kop500 || 0 },
    { key: 'pz1', label: 'PZ1', format: (item) => item.pz1 || 0 },
    { key: 'knz', label: 'KNZ', format: (item) => item.knz || 0 },
    {
        key: 'sklicka',
        label: 'Skla',
        title: 'Tvrzená skla a fólie',
        format: (item) => item.sklicka || 0,
    },
    {
        key: 'lepeni',
        label: 'LOS',
        className: 'polozky-chip--los',
        title: 'LOS – lepení; prolepenost vůči sklům + Sunshine',
        format: (item) => item.lepeni || 0,
        extra: (item, losPctFn) => {
            const pct = losPctFn(item.lepeni, item.sklicka, item.sunshine);
            return pct != null ? `${pct} %` : null;
        },
    },
    { key: 'vykupy', label: 'Výkup', className: 'polozky-chip--vykup', format: (item) => item.vykupy || 0 },
    { key: 'sunshine', label: 'Sun', className: 'polozky-chip--sun', format: (item) => item.sunshine || 0 },
    { key: 'polozky_nad_29', label: '≥29 Kč', format: (item) => item.polozky_nad_29 || 0 },
];
