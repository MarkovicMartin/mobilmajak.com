import React from 'react';
import '../styles/PeriodSegmentBar.css';

const PeriodSegmentBar = ({
    options,
    value,
    onChange,
    expanded = true,
    ariaLabel = 'Výběr období',
    className = '',
}) => (
    <div
        className={`period-segment-bar ${className}`.trim()}
        role="tablist"
        aria-label={ariaLabel}
    >
        {options.map((opt) => {
            const isActive = value === opt.id;
            return (
                <button
                    key={opt.id}
                    type="button"
                    role="tab"
                    aria-selected={isActive}
                    title={opt.title}
                    className={`period-segment${isActive && expanded ? ' period-segment--expanded' : ''}`}
                    onClick={() => onChange(opt.id)}
                >
                    {isActive && expanded ? (
                        <>
                            {opt.icon != null && (
                                <span className="period-segment-icon" aria-hidden="true">
                                    {opt.icon}
                                </span>
                            )}
                            <span className="period-segment-title">{opt.label}</span>
                        </>
                    ) : (
                        <span className="period-segment-label">{opt.label}</span>
                    )}
                </button>
            );
        })}
    </div>
);

export default PeriodSegmentBar;
