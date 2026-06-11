import React, { useMemo } from 'react';

const ASSIGNEE_GROUPS = [
    { key: 'domaci', label: 'Domácí' },
    { key: 'brigadnik', label: 'Brigádníci' },
    { key: 'ostatni', label: 'Ostatní' },
    { key: 'admini', label: 'Administrátoři' },
];

function groupAssignees(assignees) {
    const grouped = { admini: [], domaci: [], brigadnik: [], ostatni: [] };
    for (const a of assignees) {
        const key = grouped[a.skupina] ? a.skupina : 'ostatni';
        grouped[key].push(a);
    }
    return grouped;
}

export function buildAssigneeSelectOptions(assignees, placeholder) {
    const grouped = groupAssignees(assignees);
    const hasMultipleGroups = ASSIGNEE_GROUPS.filter((g) => grouped[g.key].length > 0).length > 1;
    const options = [{ value: '', label: placeholder }];
    for (const { key, label: groupLabel } of ASSIGNEE_GROUPS) {
        for (const a of grouped[key]) {
            options.push({
                value: String(a.id),
                label: hasMultipleGroups ? `${a.jmeno_plne} (${groupLabel})` : a.jmeno_plne,
            });
        }
    }
    return options;
}

export function TaskAssigneeOptions({ assignees, placeholder }) {
    const grouped = useMemo(() => groupAssignees(assignees), [assignees]);
    return (
        <>
            <option value="">{placeholder}</option>
            {ASSIGNEE_GROUPS.map(({ key, label }) =>
                grouped[key].length > 0 ? (
                    <optgroup key={key} label={label}>
                        {grouped[key].map((a) => (
                            <option key={a.id} value={a.id}>
                                {a.jmeno_plne}
                            </option>
                        ))}
                    </optgroup>
                ) : null
            )}
        </>
    );
}
