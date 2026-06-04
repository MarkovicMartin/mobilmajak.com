import React from 'react';

/**
 * Segmenty prodejců v agregaci položek:
 * - vse: všichni prodejci v období
 * - domaci: prodej na přiřazené domovské prodejně (id_prodejny = prodejna uživatele)
 * - docasni: brigádník (role BRIGADNIK) NEBO host – prodej mimo domovskou prodejnu
 */
const OPTIONS = [
    { value: 'vse', label: 'Všichni' },
    { value: 'domaci', label: 'Domácí prodejna' },
    { value: 'docasni', label: 'Host / brigádník' },
];

const PolozkySegmentFilter = ({ value, onChange }) => (
    <div className="filter-group">
        <label>Segment:</label>
        <select value={value || 'vse'} onChange={(e) => onChange(e.target.value)}>
            {OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
            ))}
        </select>
    </div>
);

export default PolozkySegmentFilter;
