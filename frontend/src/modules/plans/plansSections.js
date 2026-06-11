/** Sekce modulu Plány – pořadí záložek (výchozí: výhled). */
export const PLANS_SECTIONS = [
  { id: 'vyhled', path: 'vyhled', tabLabel: 'Výhled', icon: '📊' },
  { id: 'prodejny', path: 'plneni-prodejny', tabLabel: 'Plnění prodejny', icon: '🏪' },
  { id: 'prodejci', path: 'plneni-prodejci', tabLabel: 'Plnění prodejci', icon: '👤' },
  { id: 'plan', path: 'plan', tabLabel: 'Úprava plánu', icon: '✏️' },
];

export const DEFAULT_PLANS_SECTION = PLANS_SECTIONS[0].id;

export const plansPathForId = (id) => {
  const section = PLANS_SECTIONS.find((s) => s.id === id);
  return section ? `/plans/${section.path}` : '/plans/vyhled';
};

export const plansIdFromPath = (pathname) => {
  const segment = (pathname || '').replace(/^\/plans\/?/, '').split('/')[0] || '';
  const section = PLANS_SECTIONS.find((s) => s.path === segment);
  return section?.id || DEFAULT_PLANS_SECTION;
};

/** Zpětná kompatibilita starých hash URL (#plneni-prodejny …). */
export const plansIdFromHash = (hash) => {
  const h = hash || '';
  if (h === '#plneni-prodejny') return 'prodejny';
  if (h === '#plneni-prodejci') return 'prodejci';
  if (h === '#plan') return 'plan';
  return DEFAULT_PLANS_SECTION;
};
