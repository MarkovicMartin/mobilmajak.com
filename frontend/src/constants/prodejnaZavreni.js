import { isStoreOpenOnDate } from './oteviraciDoba';

/** Fixní dny, kdy zákon č. 223/2016 Sb. zakazuje prodej celý den (bez Velikonočního pondělí). */
export const ALWAYS_CLOSED_MM_DD = ['01-01', '05-08', '09-28', '10-28', '12-25', '12-26'];

export const RETAIL_CLOSED_SHIFT_MESSAGE =
    'V tento den mají nákupní centra podle zákona o prodejní době zavřeno. Směnu může přidat jen administrátor.';

export const CHRISTMAS_EVE_SHIFT_MESSAGE =
    '24. 12. může být prodejna otevřená jen do 12:00. Směna musí skončit nejpozději v poledne.';

export const SENIMO_HOLIDAY_MESSAGE =
    'Státní svátek – ověř, zda má zavřeno i tvé nákupní centrum.';

/** Fixní státní svátky bez Velkého pátku a Velikonočního pondělí. */
const STATE_HOLIDAY_MM_DD = [
    '01-01', '05-01', '05-08', '07-05', '07-06', '09-28', '10-28', '11-17', '12-24', '12-25', '12-26',
];

export function dateToMmDd(dateStr) {
    if (!dateStr || dateStr.length < 10) return '';
    return dateStr.slice(5, 10);
}

/** Velikonoční pondělí (anonymní gregoriánský algoritmus), YYYY-MM-DD. */
export function easterMondayIso(year) {
    const a = year % 19;
    const b = Math.floor(year / 100);
    const c = year % 100;
    const d = Math.floor(b / 4);
    const e = b % 4;
    const f = Math.floor((b + 8) / 25);
    const g = Math.floor((b - f + 1) / 3);
    const h = (19 * a + b - d - g + 15) % 30;
    const i = Math.floor(c / 4);
    const k = c % 4;
    const l = (32 + 2 * e + 2 * i - h - k) % 7;
    const m = Math.floor((a + 11 * h + 22 * l) / 451);
    const month = Math.floor((h + l - 7 * m + 114) / 31);
    const day = ((h + l - 7 * m + 114) % 31) + 1;
    const monday = new Date(year, month - 1, day);
    monday.setDate(monday.getDate() + 1);
    const mm = String(monday.getMonth() + 1).padStart(2, '0');
    const dd = String(monday.getDate()).padStart(2, '0');
    return `${monday.getFullYear()}-${mm}-${dd}`;
}

function isoDate(year, month, day) {
    const mm = String(month).padStart(2, '0');
    const dd = String(day).padStart(2, '0');
    return `${year}-${mm}-${dd}`;
}

/** Velikonoční neděle, YYYY-MM-DD. */
function easterSundayIso(year) {
    const a = year % 19;
    const b = Math.floor(year / 100);
    const c = year % 100;
    const d = Math.floor(b / 4);
    const e = b % 4;
    const f = Math.floor((b + 8) / 25);
    const g = Math.floor((b - f + 1) / 3);
    const h = (19 * a + b - d - g + 15) % 30;
    const i = Math.floor(c / 4);
    const k = c % 4;
    const l = (32 + 2 * e + 2 * i - h - k) % 7;
    const m = Math.floor((a + 11 * h + 22 * l) / 451);
    const month = Math.floor((h + l - 7 * m + 114) / 31);
    const day = ((h + l - 7 * m + 114) % 31) + 1;
    return isoDate(year, month, day);
}

function shiftIso(iso, days) {
    const [y, m, d] = iso.split('-').map(Number);
    const date = new Date(y, m - 1, d);
    date.setDate(date.getDate() + days);
    return isoDate(date.getFullYear(), date.getMonth() + 1, date.getDate());
}

export function isChristmasEve(dateStr) {
    return dateToMmDd(dateStr) === '12-24';
}

export function isCzechStateHoliday(dateStr) {
    if (!dateStr || dateStr.length < 10) return false;
    const iso = dateStr.slice(0, 10);
    if (STATE_HOLIDAY_MM_DD.includes(iso.slice(5, 10))) return true;
    const year = Number(iso.slice(0, 4));
    if (!year) return false;
    const sunday = easterSundayIso(year);
    return iso === shiftIso(sunday, -2) || iso === shiftIso(sunday, 1);
}

export function shiftCrossesNoon(casOd, casDo) {
    const od = String(casOd || '').slice(0, 5);
    const konec = String(casDo || '').slice(0, 5);
    return od >= '12:00' || konec > '12:00';
}

/** Zákonný zákaz prodeje celý den – žádná velká prodejna ani NC nemůže mít otevřeno. */
export function isRetailClosedDay(dateStr) {
    if (!dateStr || dateStr.length < 10) return false;
    const iso = dateStr.slice(0, 10);
    if (ALWAYS_CLOSED_MM_DD.includes(iso.slice(5, 10))) return true;
    const year = Number(iso.slice(0, 4));
    if (!year) return false;
    return iso === easterMondayIso(year);
}

/** always_closed | null */
export function getClosureDayKind(dateStr) {
    return isRetailClosedDay(dateStr) ? 'always_closed' : null;
}

/**
 * Má prodejna v daný den mít naplánovanou směnu (pro varování „chybí směna“)?
 * Nezávisí na ostatních státních svátcích – jen zákonný zákaz prodeje + týdenní otevírací doba.
 */
export function isStoreExpectingShift(store, dateStr) {
    if (isRetailClosedDay(dateStr)) return false;
    return isStoreOpenOnDate(store, dateStr);
}

export function getClosureNotice(dateStr, { senimo = false } = {}) {
    if (isRetailClosedDay(dateStr)) {
        return {
            kind: 'always_closed',
            title: RETAIL_CLOSED_SHIFT_MESSAGE,
            label: 'Zavřeno',
        };
    }
    if (isChristmasEve(dateStr)) {
        return {
            kind: 'short_day',
            title: CHRISTMAS_EVE_SHIFT_MESSAGE,
            label: 'do 12:00',
        };
    }
    if (senimo && isCzechStateHoliday(dateStr)) {
        return {
            kind: 'senimo_check',
            title: SENIMO_HOLIDAY_MESSAGE,
            label: 'Státní svátek – ověř NC',
        };
    }
    return null;
}
