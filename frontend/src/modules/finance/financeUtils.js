export const parseStoreChoices = (data) => {
    if (Array.isArray(data)) return data;
    if (data?.success && Array.isArray(data.stores)) return data.stores;
    if (Array.isArray(data?.stores)) return data.stores;
    if (Array.isArray(data?.results)) return data.results;
    return [];
};

/** Prodejna se vybírá zvlášť – skrýt per-prodejna řádky Reklama/Nájmy. */
export const kategorieProZarazeni = (kategorie) => {
    const byId = Object.fromEntries(kategorie.map((k) => [k.id, k]));
    return kategorie.filter((k) => {
        if (!k.parent_id) return true;
        const parent = byId[k.parent_id];
        return !parent || (parent.nazev !== 'Reklama' && parent.nazev !== 'Nájmy');
    });
};

export const storeLabel = (stores, prodejnaId) => {
    if (!prodejnaId) return '';
    const s = stores.find((x) => Number(x.id) === Number(prodejnaId));
    return s?.nazev || s?.nazev_kratkiy || s?.label || '';
};

export const ZDROJ_FILTERS = [
    { id: '', label: 'Vše' },
    { id: 'symplio_pokladna', label: 'Pokladna' },
    { id: 'fio', label: 'Účet (Fio)' },
    { id: 'raiffeisen', label: 'Účet (RB)' },
];

export const zdrojMeta = (zdroj, pokladnaLabel = '') => {
    if (zdroj === 'symplio_pokladna') {
        return {
            label: pokladnaLabel ? `Pokladna ${pokladnaLabel}` : 'Pokladna',
            short: 'kasa',
            pokladna: pokladnaLabel || '',
            rowClass: 'finance-row--kasa',
            badgeClass: 'finance-badge--kasa',
        };
    }
    if (zdroj === 'fio') {
        return { label: 'Účet', short: 'Fio', pokladna: '', rowClass: 'finance-row--fio', badgeClass: 'finance-badge--fio' };
    }
    if (zdroj === 'raiffeisen') {
        return {
            label: pokladnaLabel ? `Raiffeisen ${pokladnaLabel}` : 'Raiffeisen',
            short: 'RB',
            pokladna: pokladnaLabel || '',
            rowClass: 'finance-row--fio',
            badgeClass: 'finance-badge--fio',
        };
    }
    return { label: zdroj || '–', short: zdroj || '–', pokladna: '', rowClass: '', badgeClass: '' };
};

export const pokladnaZnacka = (p) => (
    p?.zdroj === 'symplio_pokladna' ? (p.pokladna_label || '') : ''
);

/** Krátká značka zdroje v analytice: fio / RB 0155 / kasa. */
export const zdrojPoznamka = (p) => {
    if (!p) return '';
    if (p.zdroj === 'symplio_pokladna') {
        return p.pokladna_label ? `kasa ${p.pokladna_label}` : 'kasa';
    }
    if (p.zdroj === 'raiffeisen') {
        return p.pokladna_label ? `RB ${p.pokladna_label}` : 'RB';
    }
    if (p.zdroj === 'fio') return 'fio';
    return p.zdroj || '';
};

export const movementLabel = (p) => {
    if (p.zdroj === 'symplio_pokladna') {
        return p.popis || p.zprava || '–';
    }
    return p.zprava || p.popis || '–';
};

export const countByZdroj = (items) => ({
    all: items.length,
    fio: items.filter((p) => p.zdroj === 'fio').length,
    raiffeisen: items.filter((p) => p.zdroj === 'raiffeisen').length,
    symplio_pokladna: items.filter((p) => p.zdroj === 'symplio_pokladna').length,
    kasa: items.filter((p) => p.zdroj === 'symplio_pokladna').length,
});
