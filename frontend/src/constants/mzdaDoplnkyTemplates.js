/** Rychlé šablony mzdových doplňků (body). */
export const MZDA_DOPLNEK_TEMPLATES = [
    {
        kod: 'vedouci_pobocky',
        nazev: 'Odměna vedoucí pobočky',
        castka: 2000,
    },
];

export function createDoplnekFromTemplate(template) {
    return {
        kod: template.kod,
        nazev: template.nazev,
        castka: template.castka,
    };
}

export function sumDoplnkyBody(doplnky) {
    return (doplnky || []).reduce((s, d) => s + (Number(d.castka) || 0), 0);
}
