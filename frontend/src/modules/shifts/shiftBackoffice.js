/** Backoffice uživatel – bez domovské prodejny (nebo výslovně Michaela Smčková). */
export const isBackofficeUser = (user) => {
    if (!user) return false;
    const prijmeni = (user.prijmeni || '').trim().toLowerCase();
    if (prijmeni === 'smčková' || prijmeni === 'smckova') return true;
    if (user.role === 'ADMIN') return false;
    return !user.prodejna_id && ['PRODEJCE', 'VEDOUCI'].includes(user.role);
};
