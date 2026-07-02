export const DNY_TYDNE = [
    { key: 'po', label: 'Po' },
    { key: 'ut', label: 'Út' },
    { key: 'st', label: 'St' },
    { key: 'ct', label: 'Čt' },
    { key: 'pa', label: 'Pá' },
    { key: 'so', label: 'So' },
    { key: 'ne', label: 'Ne' },
];

export const VYCHOZI_OTEVIRACI_OD = '08:00';
export const VYCHOZI_OTEVIRACI_DO = '20:00';

export function defaultOteviraciDoba() {
    return {
        stejne_pro_vsechny: true,
        vychozi: { od: VYCHOZI_OTEVIRACI_OD, do: VYCHOZI_OTEVIRACI_DO },
        dny: Object.fromEntries(DNY_TYDNE.map((d) => [d.key, null])),
    };
}

/** null = výchozí hodiny; { zavreno: true } = zavřeno; { od, do } = vlastní rozpad */
export function effectiveDenHours(den, vychozi) {
    if (den?.zavreno) {
        return { zavreno: true, od: '', do: '' };
    }
    const v = vychozi || {};
    return {
        zavreno: false,
        od: (den?.od || v.od || VYCHOZI_OTEVIRACI_OD).slice(0, 5),
        do: (den?.do || v.do || VYCHOZI_OTEVIRACI_DO).slice(0, 5),
        usesVychozi: !den || (!den.od && !den.do && !den.zavreno),
    };
}

export function normalizeOteviraciDoba(raw) {
    if (!raw || typeof raw !== 'object') {
        return defaultOteviraciDoba();
    }
    const vychozi = raw.vychozi || {};
    const vychoziNorm = {
        od: (vychozi.od || VYCHOZI_OTEVIRACI_OD).slice(0, 5),
        do: (vychozi.do || VYCHOZI_OTEVIRACI_DO).slice(0, 5),
    };
    return {
        stejne_pro_vsechny: raw.stejne_pro_vsechny !== false,
        vychozi: vychoziNorm,
        dny: DNY_TYDNE.reduce((acc, { key }) => {
            const day = (raw.dny || {})[key];
            if (!day) {
                acc[key] = null;
            } else if (day.zavreno) {
                acc[key] = { zavreno: true };
            } else {
                acc[key] = {
                    od: (day.od || vychoziNorm.od).slice(0, 5),
                    do: (day.do || vychoziNorm.do).slice(0, 5),
                };
            }
            return acc;
        }, {}),
    };
}

const DOW_TO_DEN_KEY = ['ne', 'po', 'ut', 'st', 'ct', 'pa', 'so'];

/** Má prodejna vyplněnou strukturovanou otevírací dobu (ne prázdný JSON)? */
export function hasStructuredOteviraciDoba(raw) {
    if (!raw || typeof raw !== 'object') return false;
    if (!Object.keys(raw).length) return false;
    if (raw.dny && Object.values(raw.dny).some((d) => d != null)) return true;
    if (raw.stejne_pro_vsechny === false) return true;
    if (raw.vychozi?.od || raw.vychozi?.do) return true;
    return raw.stejne_pro_vsechny !== undefined;
}

function isStoreOpenOnDateLegacy(store, denKey) {
    if (!store?.otevreno_od && !store?.otevreno_do) return true;
    return denKey !== 'ne';
}

/** Je prodejna v daný den otevřená dle nastavené otevírací doby? */
export function isStoreOpenOnDate(store, dateStr) {
    const parsed = new Date(`${dateStr}T12:00:00`);
    if (Number.isNaN(parsed.getTime())) return true;
    const denKey = DOW_TO_DEN_KEY[parsed.getDay()];

    if (hasStructuredOteviraciDoba(store?.oteviraci_doba)) {
        const cfg = normalizeOteviraciDoba(store.oteviraci_doba);
        const eff = effectiveDenHours(cfg.dny[denKey], cfg.vychozi);
        return !eff.zavreno;
    }

    return isStoreOpenOnDateLegacy(store, denKey);
}
