import { isStoreOpenOnDate } from './oteviraciDoba';

/** Vždy zavřeno (všechny prodejny vč. Globus). */
export const ALWAYS_CLOSED_MM_DD = ['01-01', '12-25', '12-26'];

/** NC typicky zavřeno – Globus obvykle otevřen, u NC ověřit / neplánovat směnu. */
export const NC_TYPICALLY_CLOSED_MM_DD = ['05-08', '09-28', '10-28'];

export function dateToMmDd(dateStr) {
    if (!dateStr || dateStr.length < 10) return '';
    return dateStr.slice(5, 10);
}

export function isGlobusStore(store) {
    const name = (store?.nazev_kratkiy || store?.nazev || '').trim().toLowerCase();
    return name === 'globus';
}

export function isNakupniCentrumStore(store) {
    return Boolean(store) && !isGlobusStore(store);
}

/** always_closed | nc_verify_closed | null */
export function getClosureDayKind(dateStr) {
    const mmdd = dateToMmDd(dateStr);
    if (ALWAYS_CLOSED_MM_DD.includes(mmdd)) return 'always_closed';
    if (NC_TYPICALLY_CLOSED_MM_DD.includes(mmdd)) return 'nc_verify_closed';
    return null;
}

/**
 * Má prodejna v daný den mít naplánovanou směnu (pro varování „chybí směna“)?
 * Nezávisí na státním svátku v kalendáři – jen fixní zavíračky + týdenní otevírací doba.
 */
export function isStoreExpectingShift(store, dateStr) {
    const kind = getClosureDayKind(dateStr);
    if (kind === 'always_closed') return false;
    if (kind === 'nc_verify_closed' && isNakupniCentrumStore(store)) return false;
    return isStoreOpenOnDate(store, dateStr);
}

export function getClosureNotice(dateStr, { stores = [], allStores = false, prodejnaId = null, userStore = null } = {}) {
    const kind = getClosureDayKind(dateStr);
    if (!kind) return null;

    if (kind === 'always_closed') {
        return {
            kind,
            title: 'V tento den je prodejna vždy zavřena.',
            label: 'Zavřeno',
        };
    }

    if (kind === 'nc_verify_closed') {
        if (userStore && isGlobusStore(userStore)) {
            return null;
        }
        if (!allStores && prodejnaId && prodejnaId !== 'vse') {
            const store = stores.find((s) => String(s.id) === String(prodejnaId));
            if (store && isGlobusStore(store)) return null;
        }
        return {
            kind,
            title: 'Státní svátek – ověř, zda má zavřeno i tvé nákupní centrum.',
            label: 'Státní svátek – ověř NC',
        };
    }

    return null;
}
