/** Výchozí mzdové hodnoty (body) – shodné s backend/users/mzda_utils.py */
export const PRODEJCE_ZAKLAD_BODY = 14000;
export const VYCHODIL_ZAKLAD_BODY = 17000;
export const BRIGADNIK_DEFAULT_BODY_ZA_HODINU = 100;

export function isVychodilPrijmeni(prijmeni) {
    return (prijmeni || '').trim().toLowerCase() === 'vychodil';
}

export function defaultMzdaZakladForRole(role, prijmeni = '') {
    if (role === 'BRIGADNIK') {
        return BRIGADNIK_DEFAULT_BODY_ZA_HODINU;
    }
    if (role === 'PRODEJCE' || role === 'VEDOUCI') {
        return isVychodilPrijmeni(prijmeni) ? VYCHODIL_ZAKLAD_BODY : PRODEJCE_ZAKLAD_BODY;
    }
    return null;
}
