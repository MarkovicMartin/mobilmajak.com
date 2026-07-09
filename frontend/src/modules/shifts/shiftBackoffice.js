/** Virtuální pobočka pro backoffice zaměstnance (např. bez domovské prodejny). */
export const BACKOFFICE_LOCATION = 'backoffice';

/** Barva virtuální pobočky Backoffice v kalendáři směn. */
export const BACKOFFICE_CALENDAR_COLOR = '#5c4d8a';

export const isBackofficeCalendarFilter = (prodejna) => (
    String(prodejna || '').trim().toLowerCase() === BACKOFFICE_LOCATION
);

/** Režim práce admin účtu – home office, ruční popis, nebo fyzická prodejna. */
export const ADMIN_WORK_HOME_OFFICE = 'home_office';
export const ADMIN_WORK_BACKOFFICE = 'backoffice';
export const ADMIN_WORK_STORE = 'store';

export const isBackofficeUser = (user) => {
    if (!user) return false;
    const prijmeni = (user.prijmeni || '').trim().toLowerCase();
    if (['smčková', 'smckova', 'smrčková', 'smrckova'].includes(prijmeni)) return true;
    if (user.role === 'ADMIN') return false;
    return !user.prodejna_id && ['PRODEJCE', 'VEDOUCI'].includes(user.role);
};

export const isAdminUser = (user) => user?.role === 'ADMIN';

export const isHomeOfficePozice = (pozice) => pozice === 'home_office';

export const isBackofficeLocation = (prodejna) => prodejna === BACKOFFICE_LOCATION;

export const getAdminWorkMode = (prodejna, poziceSmeny) => {
    if (isHomeOfficePozice(poziceSmeny)) return ADMIN_WORK_HOME_OFFICE;
    if (isBackofficeLocation(prodejna) || poziceSmeny === 'backoffice') return ADMIN_WORK_BACKOFFICE;
    return ADMIN_WORK_STORE;
};

export const isBackofficeWorkShift = (user, typSmeny, poziceSmeny, prodejna, adminWorkMode = null) => {
    if (typSmeny !== 'prace') return false;
    if (isAdminUser(user) && adminWorkMode) {
        return adminWorkMode === ADMIN_WORK_BACKOFFICE;
    }
    if (isBackofficeLocation(prodejna)) return true;
    if (poziceSmeny === 'backoffice' && (prodejna == null || isBackofficeLocation(prodejna))) return true;
    return false;
};

export const isHomeOfficeWorkShift = (user, typSmeny, poziceSmeny, adminWorkMode = null) => {
    if (typSmeny !== 'prace') return false;
    if (isAdminUser(user) && adminWorkMode) {
        return adminWorkMode === ADMIN_WORK_HOME_OFFICE;
    }
    return isHomeOfficePozice(poziceSmeny);
};
