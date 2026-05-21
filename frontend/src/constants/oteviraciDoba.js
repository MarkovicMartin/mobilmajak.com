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
