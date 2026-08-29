import React from 'react';

export const RATE_MODES = [
    { value: 'total', label: 'Celkem' },
    { value: 'per_hour', label: 'Za hodinu' },
    { value: 'both', label: 'Obě' },
];

const fmtCell = (v) => {
    if (v == null || v === '') return '—';
    const n = Number(v);
    if (Number.isNaN(n)) return String(v);
    return n.toLocaleString('cs-CZ', { maximumFractionDigits: 2 });
};

/** Formát buňky podle režimu Celkem / Za hodinu / Obě. */
export const formatCompareValue = (total, perHour, rateMode, { isHours = false } = {}) => {
    if (isHours) return fmtCell(total);
    if (rateMode === 'per_hour') return fmtCell(perHour);
    if (rateMode === 'both') {
        if (total == null && perHour == null) return '—';
        return `${fmtCell(total)} · ${fmtCell(perHour)}/h`;
    }
    return fmtCell(total);
};

const CompareRateToggle = ({ value, onChange }) => (
    <div className="coaching-rate-toggle" role="group" aria-label="Zobrazení výkonu">
        {RATE_MODES.map((m) => (
            <button
                key={m.value}
                type="button"
                className={`coaching-rate-toggle__btn${value === m.value ? ' is-active' : ''}`}
                onClick={() => onChange(m.value)}
            >
                {m.label}
            </button>
        ))}
    </div>
);

export default CompareRateToggle;
