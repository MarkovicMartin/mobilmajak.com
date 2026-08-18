export const isSenimoStore = (store) => (store?.nazev || '').trim() === 'Senimo';

export const extraPoziceSelectEnabled = (store) => Boolean(store);
