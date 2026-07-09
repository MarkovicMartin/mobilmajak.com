/** Backoffice uživatel – bez domovské prodejny (nebo výslovně Smrčková/Smčková). */
export const BACKOFFICE_LOCATION = 'backoffice';

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

export const isBackofficeWorkShift = (user, typSmeny, poziceSmeny, prodejna) => {
    if (typSmeny !== 'prace') return false;
    if (isBackofficeLocation(prodejna)) return true;
    if (poziceSmeny === 'backoffice') return true;
    return isBackofficeUser(user) && typSmeny === 'prace';
};
