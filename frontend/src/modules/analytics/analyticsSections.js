/** Sekce analytiky – sdílené pro záložky v AnalyticsNav */
export const ANALYTICS_SECTIONS = [
    { id: 'celkova-cisla', label: 'Celková čísla', tabLabel: 'Celková čísla', icon: '📈' },
    { id: 'prodejny-polozky', label: 'Prodejny – Položky', tabLabel: 'Položky', icon: '📱' },
    { id: 'servis', label: 'Servis', tabLabel: 'Servis', icon: '🔧' },
    { id: 'prodejni-analytika', label: 'Prodejní analytika', tabLabel: 'Prodejní analytika', icon: '🎯' },
    { id: 'prodejny-traffic', label: 'Prodejny & Zákazníci', tabLabel: 'Zákazníci', icon: '🧑‍🤝‍🧑' },
    { id: 'eshop', label: 'E-shop', tabLabel: 'E-shop', icon: '🛒' },
];

export const DEFAULT_ANALYTICS_SECTION = ANALYTICS_SECTIONS[0].id;

export const getAnalyticsSection = (id) =>
    ANALYTICS_SECTIONS.find((s) => s.id === id) || null;
