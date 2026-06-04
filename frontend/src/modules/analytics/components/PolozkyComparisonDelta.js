import React from 'react';

const fmtPct = (left, right) => {
    const a = Number(left) || 0;
    const b = Number(right) || 0;
    if (a === 0 && b === 0) return '—';
    if (a === 0) return '+∞';
    const pct = ((b - a) / a) * 100;
    const sign = pct > 0 ? '+' : '';
    return `${sign}${pct.toFixed(1)} %`;
};

const fmtAbs = (left, right) => {
    const d = (Number(right) || 0) - (Number(left) || 0);
    const sign = d > 0 ? '+' : '';
    return `${sign}${d}`;
};

/** Delta badge u souhrnných karet nebo metriky prodejce. */
export const PolozkyDeltaBadge = ({ left, right, format = 'number' }) => {
    if (left == null || right == null) return null;
    const display = format === 'currency'
        ? fmtAbs(left, right)
        : fmtAbs(left, right);
    const pct = fmtPct(left, right);
    const positive = (Number(right) || 0) >= (Number(left) || 0);
    return (
        <span className={`polozky-delta${positive ? ' polozky-delta--up' : ' polozky-delta--down'}`} title={`${display} (${pct})`}>
            {pct}
        </span>
    );
};

const PolozkyComparisonDelta = ({ leftTotals, rightTotals, keys }) => {
    if (!leftTotals || !rightTotals) return null;
    return (
        <div className="polozky-comparison-delta-row">
            {keys.map((key) => (
                <div key={key} className="polozky-comparison-delta-item">
                    <span className="polozky-comparison-delta-label">{key}</span>
                    <PolozkyDeltaBadge left={leftTotals[key]} right={rightTotals[key]} />
                </div>
            ))}
        </div>
    );
};

export default PolozkyComparisonDelta;
