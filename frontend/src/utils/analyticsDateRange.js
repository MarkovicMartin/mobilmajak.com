/** Validace a normalizace ISO dat (YYYY-MM-DD) pro analytické filtry. */

export const isValidISODate = (str) => {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(str)) return false;
    const [y, m, d] = str.split('-').map(Number);
    const dt = new Date(y, m - 1, d);
    return dt.getFullYear() === y && dt.getMonth() === m - 1 && dt.getDate() === d;
};

export const formatISODate = (d) =>
    `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;

/** Vrátí { start_date, end_date } nebo null při neplatném vstupu. */
export const normalizeDateRange = (start_date, end_date) => {
    if (!isValidISODate(start_date) || !isValidISODate(end_date)) {
        return null;
    }
    let start = start_date;
    let end = end_date;
    if (new Date(start) > new Date(end)) {
        [start, end] = [end, start];
    }
    return { start_date: start, end_date: end };
};

export const INVALID_DATE_MESSAGE = 'Neplatné datum. Zkontrolujte prosím zadání.';
