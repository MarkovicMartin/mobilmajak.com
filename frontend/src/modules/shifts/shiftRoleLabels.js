/**
 * Zobrazení role směny místo generického „Práce“.
 * Brigádník: Výpomoc / Prodejce; servisní pozice; backoffice; absence: Dovolená / Nemoc.
 */
export const shiftRoleLabel = (shift, { short = false } = {}) => {
    if (!shift) return '—';
    const typ = shift.typ_smeny;
    if (typ === 'dovolena') return 'Dovolená';
    if (typ === 'nemoc') return 'Nemoc';
    if (typ !== 'prace') return typ;

    if (shift.pozice_smeny === 'backoffice') return 'Backoffice';
    if (shift.pozice_smeny === 'home_office') return short ? 'Home off.' : 'Home office';
    if (shift.pozice_smeny === 'servis') {
        if (short) {
            return shift.servis_uroven === 'zauceni' ? 'Servis (zašk.)' : 'Servis';
        }
        return shift.servis_uroven === 'zauceni'
            ? 'Servisní technik (zaškolení)'
            : 'Servisní technik';
    }
    if (shift.brigadnik_rezim === 'vypomoc') return 'Výpomoc';
    return 'Prodejce';
};
