/** Admin sekce dostupné z ⚙️ v dock liště */
export const ADMIN_SECTIONS = [
    { id: 'users', name: 'Uživatelé', icon: '👥', description: 'Správa uživatelů systému' },
    { id: 'categories', name: 'Kategorie', icon: '🏷️', description: 'Správa kategorií novinek' },
    { id: 'stores', name: 'Prodejny', icon: '🏪', description: 'Správa prodejen' },
    { id: 'tickets', name: 'Tikety', icon: '🐛', description: 'Správa tiketů od prodejců' },
];

export const getAdminSectionFromPath = (pathname) =>
    ADMIN_SECTIONS.find((s) => pathname === `/${s.id}`) || null;

export const isAdminSectionPath = (pathname) => !!getAdminSectionFromPath(pathname);
