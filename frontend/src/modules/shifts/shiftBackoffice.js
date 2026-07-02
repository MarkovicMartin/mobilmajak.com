/** Backoffice uživatel – bez domovské prodejny (nebo výslovně Smrčková/Smčková). */
export const isBackofficeUser = (user) => {
    if (!user) return false;
    const prijmeni = (user.prijmeni || '').trim().toLowerCase();
    if (['smčková', 'smckova', 'smrčková', 'smrckova'].includes(prijmeni)) return true;
    if (user.role === 'ADMIN') return false;
    return !user.prodejna_id && ['PRODEJCE', 'VEDOUCI'].includes(user.role);
};

export const isAdminUser = (user) => user?.role === 'ADMIN';

export const isHomeOfficePozice = (pozice) => pozice === 'home_office';
