/** Vícepráce – Symplio kód P63615 (shodně s backend viceprace_config.py) */
export const VICEPRACE_KOD = 'P63615';
export const VICEPRACE_LABEL = 'Vícepráce';
export const VICEPRACE_LEADER_LABEL = 'Nejlepší dýškař';
/** Nadpis stat karty v žebříčku bodů */
export const VICEPRACE_TOP_CARD_TITLE = 'Top dýškař';

/** Součet obratu P63615 (Počet_kusu × cena s DPH), ne počet kusů */
export const formatVicepraceObrat = (value) => {
    const n = Number(value) || 0;
    if (n <= 0) return '—';
    return new Intl.NumberFormat('cs-CZ', {
        style: 'currency',
        currency: 'CZK',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
    }).format(Math.round(n));
};
