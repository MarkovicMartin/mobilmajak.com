/**
 * České skloňování „bod / body / bodů“.
 */
export function formatBodyCount(value) {
    const n = Math.abs(Number(value) || 0);
    const abs = Math.floor(n);
    if (abs === 1) return '1 bod';
    if (abs >= 2 && abs <= 4) return `${formatNumber(n)} body`;
    return `${formatNumber(n)} bodů`;
}

export function formatNumber(value) {
    const n = Number(value);
    if (Number.isNaN(n)) return '0';
    if (Number.isInteger(n)) return String(n);
    return n.toLocaleString('cs-CZ', { maximumFractionDigits: 2 });
}

export function formatBodyLabel(value) {
    return formatBodyCount(value);
}

/** Číslo bodů bez slova „bod/body/bodů“ (tabulky výplaty). */
export function formatPoints(value) {
    return formatNumber(value);
}
