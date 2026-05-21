/**
 * Číselné pole bez změny hodnoty kolečkem myši při scrollu stránky.
 * Spinner (šipky) se skryje přes CSS třídu input-manual-number.
 */
export function preventNumberInputWheel(e) {
    e.currentTarget.blur();
}

export function manualNumberInputClass(extra = '') {
    return extra ? `input-manual-number ${extra}` : 'input-manual-number';
}
