import React, { useMemo } from 'react';

const ASSIGNEE_GROUPS = [
    { key: 'admini', label: 'Administrátoři' },
    { key: 'domaci', label: 'Domácí' },
    { key: 'brigadnik', label: 'Brigádníci' },
    { key: 'ostatni', label: 'Ostatní' },
];

function groupAssignees(assignees) {
    const grouped = { admini: [], domaci: [], brigadnik: [], ostatni: [] };
    for (const a of assignees) {
        const key = grouped[a.skupina] ? a.skupina : 'ostatni';
        grouped[key].push(a);
    }
    return grouped;
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
