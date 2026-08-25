/** Sekce analytiky – sdílené pro záložky v AnalyticsNav */
export const ANALYTICS_SECTIONS = [
    { id: 'celkova-cisla', label: 'Celková čísla', tabLabel: 'Čísla', icon: '📈' },
    { id: 'prodejny-polozky', label: 'Prodejny – Položky', tabLabel: 'Položky', icon: '📱' },
    { id: 'servis', label: 'Servis', tabLabel: 'Servis', icon: '🔧' },
    { id: 'prodejni-analytika', label: 'Prodejní analytika', tabLabel: 'Prodeje', icon: '🎯' },
    { id: 'prodejny-traffic', label: 'Prodejny & Zákazníci', tabLabel: 'Návštěvy', icon: '🧑‍🤝‍🧑' },
    { id: 'zasilkovna-konverze', label: 'Zásilkovna', tabLabel: 'Zásilkovna', icon: '📦' },
    { id: 'eshop', label: 'E-shop', tabLabel: 'E-shop', icon: '🛒' },
    { id: 'naklady', label: 'Náklady', tabLabel: 'Náklady', icon: '💸' },
];

export const DEFAULT_ANALYTICS_SECTION = ANALYTICS_SECTIONS[0].id;

export const getAnalyticsSection = (id) =>
    ANALYTICS_SECTIONS.find((s) => s.id === id) || null;
