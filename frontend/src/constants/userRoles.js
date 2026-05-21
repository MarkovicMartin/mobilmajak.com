/** Systémové role WebUser – popisky pro UI. */
export const USER_ROLE_OPTIONS = [
    { value: 'PRODEJCE', label: 'Prodejce' },
    { value: 'BRIGADNIK', label: 'Brigádník' },
    { value: 'ADMIN', label: 'Administrátor' },
];

export const BRIGADNIK_DEFAULT_BODY_ZA_HODINU = 80;

export function roleLabel(role) {
    if (role === 'ADMIN') return 'Administrátor';
    if (role === 'BRIGADNIK') return 'Brigádník';
    if (role === 'VEDOUCI') return 'Vedoucí';
    return 'Prodejce';
}

export function isBrigadnikRole(role) {
    return role === 'BRIGADNIK';
}
