/**
 * Plánované částky v systému jsou zadávány jako obrat s 21 % DPH.
 * Převod na základ bez DPH: částka_s_DPH / 1.21
 */
export const DPH_KOEF_S_NA_BEZ = 1.21;

/**
 * @param {number|string} sDph
 * @returns {number} zaokrouhleno na celé Kč
 */
export function castkaBezDphZCelkem(sDph) {
    const n = Number(sDph);
    if (!Number.isFinite(n) || n === 0) return 0;
    return Math.round(n / DPH_KOEF_S_NA_BEZ);
}
