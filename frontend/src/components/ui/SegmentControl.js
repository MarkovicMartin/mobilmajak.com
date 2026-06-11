import React from 'react';
import './SegmentControl.css';

/**
 * Segmentovaný přepínač období / režimů.
 * legacy=true používá třídy period-segment-bar pro zpětnou kompatibilitu.
 */
const SegmentControl = ({
    options,
    value,
    onChange,
    expanded = true,
    ariaLabel = 'Výběr období',
    className = '',
    legacy = false,
}) => {
    const rootClass = legacy
        ? `period-segment-bar ${className}`.trim()
        : `ui-segment-control ${className}`.trim();
    const segmentBase = legacy ? 'period-segment' : 'ui-segment-control__item';
    const segmentExpanded = legacy ? ' period-segment--expanded' : ' ui-segment-control__item--active';
    const iconClass = legacy ? 'period-segment-icon' : 'ui-segment-control__icon';
    const titleClass = legacy ? 'period-segment-title' : 'ui-segment-control__title';
    const labelClass = legacy ? 'period-segment-label' : 'ui-segment-control__label';

    return (
        <div className={rootClass} role="tablist" aria-label={ariaLabel}>
            {options.map((opt) => {
                const isActive = value === opt.id;
                return (
                    <button
                        key={opt.id}
                        type="button"
                        role="tab"
                        aria-selected={isActive}
                        title={opt.title}
                        className={`${segmentBase}${isActive && expanded ? segmentExpanded : ''}`}
                        onClick={() => onChange(opt.id)}
                    >
                        {isActive && expanded ? (
                            <>
                                {opt.icon != null && (
                                    <span className={iconClass} aria-hidden="true">
                                        {opt.icon}
                                    </span>
                                )}
                                <span className={titleClass}>{opt.label}</span>
                            </>
                        ) : (
                            <span className={labelClass}>{opt.label}</span>
                        )}
                    </button>
                );
            })}
        </div>
    );
};

export default SegmentControl;
