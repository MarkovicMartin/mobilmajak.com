import React from 'react';

/** Sdílená třída záložek v hlavičce modulu (jako Můj profil). */
export const MODULE_PAGE_TABS_CLASS = 'module-page-tabs';

export function sectionTabIcon(icon) {
    if (icon == null) return null;
    if (typeof icon === 'string' && icon.startsWith('fa-')) {
        return <i className={`fas ${icon}`} aria-hidden="true" />;
    }
    return icon;
}

/** URL záložky – analytika, plány, výkony. */
export function sectionsToUrlTabs(sections, { pathFor, endFor } = {}) {
    return sections.map((section) => ({
        id: section.id,
        label: section.tabLabel ?? section.label,
        icon: sectionTabIcon(section.icon),
        to: pathFor(section),
        end: endFor ? endFor(section) : false,
    }));
}

/** Stavové záložky – profil, směny. */
export function sectionsToStateTabs(sections) {
    return sections.map((section) => ({
        id: section.id,
        label: section.tabLabel ?? section.label,
        icon: sectionTabIcon(section.icon),
    }));
}
