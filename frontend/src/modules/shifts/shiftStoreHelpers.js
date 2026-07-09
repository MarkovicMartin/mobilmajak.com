export const isSenimoStore = (store) => (store?.nazev || '').trim() === 'Senimo';

export const extraPoziceSelectEnabled = (store) => {
    return Boolean(store?.povolena_pozice_servis) || isSenimoStore(store);
};
