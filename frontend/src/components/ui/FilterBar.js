import React from 'react';
import SegmentControl from './SegmentControl';
import DateRangePicker from './DateRangePicker';
import {
    QUICK_RANGE_PRESETS,
    computeQuickRange,
} from '../../utils/analyticsQuickRange';
import './FilterBar.css';

/**
 * Horizontální řádek filtrů – presety období, vlastní rozsah, refresh, volitelné sloty.
 */
const FilterBar = ({
    startDate,
    endDate,
    preset = 'custom',
    onRangeChange,
    onDateErrorChange,
    onRefresh,
    refreshDisabled = false,
    refreshLoading = false,
    refreshLabel = 'Obnovit',
    className = '',
    children,
    presets = QUICK_RANGE_PRESETS,
    legacy = false,
}) => {
    const isCustom = !preset || preset === 'custom';

    const handlePresetChange = (id) => {
        const range = computeQuickRange(id);
        if (!range) return;
        onDateErrorChange?.('');
        onRangeChange?.({ ...range, preset: id });
    };

    const handleDateApply = (range) => {
        onRangeChange?.({ ...range, preset: 'custom' });
    };

    const rootClass = legacy
        ? `date-filter-bar ${className}`.trim()
        : `ui-filter-bar ${className}`.trim();
    const refreshClass = legacy ? 'date-filter-bar__refresh' : 'ui-filter-bar__refresh btn btn--ghost btn--sm';

    return (
        <div className={rootClass}>
            <SegmentControl
                options={presets}
                value={isCustom ? null : preset}
                onChange={handlePresetChange}
                ariaLabel="Rychlé volby období"
                legacy={legacy}
            />
            {isCustom && (
                <DateRangePicker
                    startDate={startDate}
                    endDate={endDate}
                    onApply={handleDateApply}
                    onErrorChange={onDateErrorChange}
                    showError={false}
                    variant="inline"
                    legacy={legacy}
                />
            )}
            {children}
            {onRefresh && (
                <button
                    type="button"
                    className={refreshClass}
                    onClick={onRefresh}
                    disabled={refreshDisabled}
                >
                    {refreshLoading ? '⏳' : '🔄'} {refreshLabel}
                </button>
            )}
        </div>
    );
};

export default FilterBar;
