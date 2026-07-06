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
];

export const zdrojMeta = (zdroj) => {
    if (zdroj === 'symplio_pokladna') {
        return { label: 'Pokladna', short: 'kasa', rowClass: 'finance-row--kasa', badgeClass: 'finance-badge--kasa' };
    }
    if (zdroj === 'fio') {
        return { label: 'Účet', short: 'Fio', rowClass: 'finance-row--fio', badgeClass: 'finance-badge--fio' };
    }
    return { label: zdroj || '–', short: zdroj || '–', rowClass: '', badgeClass: '' };
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
    kasa: items.filter((p) => p.zdroj === 'symplio_pokladna').length,
});
