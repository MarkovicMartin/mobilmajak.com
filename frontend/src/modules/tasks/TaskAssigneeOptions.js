import React, { useMemo } from 'react';

const STATIC_GROUPS = [
    { key: 'domaci', label: 'Domácí' },
    { key: 'brigadnik', label: 'Brigádníci' },
    { key: 'ostatni', label: 'Ostatní' },
    { key: 'admini', label: 'Administrátoři' },
    { key: 'backoffice', label: 'Backoffice' },
];

function groupAssignees(assignees) {
    const grouped = {
        admini: [],
        backoffice: [],
        domaci: [],
        brigadnik: [],
        ostatni: [],
        prodejny: [],
    };
    const storeMap = new Map();

    for (const a of assignees) {
        if (a.skupina === 'prodejna' && a.prodejna_id != null) {
            const key = String(a.prodejna_id);
            if (!storeMap.has(key)) {
                storeMap.set(key, {
                    key: `prodejna-${key}`,
                    label: a.prodejna_nazev || `Prodejna ${key}`,
                    items: [],
                });
            }
            storeMap.get(key).items.push(a);
            continue;
        }
        const bucket = grouped[a.skupina] ? a.skupina : 'ostatni';
        grouped[bucket].push(a);
    }

    grouped.prodejny = [...storeMap.values()].sort((a, b) =>
        a.label.localeCompare(b.label, 'cs'),
    );
    return grouped;
}

function orderedGroups(grouped) {
    const out = [];
    if (grouped.admini.length) out.push({ key: 'admini', label: 'Administrátoři', items: grouped.admini });
    if (grouped.backoffice.length) out.push({ key: 'backoffice', label: 'Backoffice', items: grouped.backoffice });
    for (const store of grouped.prodejny) {
        out.push(store);
    }
    for (const { key, label } of STATIC_GROUPS) {
        if (key === 'admini' || key === 'backoffice') continue;
        if (grouped[key]?.length) out.push({ key, label, items: grouped[key] });
    }
    return out;
}

export function buildAssigneeSelectOptions(assignees, placeholder) {
    const grouped = groupAssignees(assignees);
    const groups = orderedGroups(grouped);
    const hasMultipleGroups = groups.length > 1;
    const options = [{ value: '', label: placeholder }];
    for (const group of groups) {
        for (const a of group.items) {
            options.push({
                value: String(a.id),
                label: hasMultipleGroups ? `${a.jmeno_plne} (${group.label})` : a.jmeno_plne,
            });
        }
    }
    return options;
}

export function TaskAssigneeOptions({ assignees, placeholder }) {
    const groups = useMemo(() => orderedGroups(groupAssignees(assignees)), [assignees]);
    return (
        <>
            <option value="">{placeholder}</option>
            {groups.map((group) => (
                <optgroup key={group.key} label={group.label}>
                    {group.items.map((a) => (
                        <option key={a.id} value={a.id}>
                            {a.jmeno_plne}
                        </option>
                    ))}
                </optgroup>
            ))}
        </>
    );
}
