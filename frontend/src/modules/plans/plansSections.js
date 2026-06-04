/** Sekce modulu Plány – pořadí záložek (výchozí: výhled). */
export const PLANS_SECTIONS = [
  { id: 'vyhled', tabLabel: 'Výhled', icon: '📊' },
  { id: 'prodejny', tabLabel: 'Plnění prodejny', icon: '🏪' },
  { id: 'prodejci', tabLabel: 'Plnění prodejci', icon: '👤' },
  { id: 'plan', tabLabel: 'Úprava plánu', icon: '✏️' },
];

export const DEFAULT_PLANS_SECTION = PLANS_SECTIONS[0].id;
