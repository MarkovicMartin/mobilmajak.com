import React from 'react';
import AnalyticsDateRange from './AnalyticsDateRange';
import PeriodSegmentBar from './PeriodSegmentBar';
import {
    QUICK_RANGE_PRESETS,
    computeQuickRange,
} from '../utils/analyticsQuickRange';
import '../styles/DateFilterBar.css';

const DateFilterBar = ({
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

    return (
        <div className={`date-filter-bar ${className}`.trim()}>
            <PeriodSegmentBar
                options={QUICK_RANGE_PRESETS}
                value={isCustom ? null : preset}
                onChange={handlePresetChange}
                ariaLabel="Rychlé volby období"
            />
            {isCustom && (
                <AnalyticsDateRange
                    startDate={startDate}
                    endDate={endDate}
                    onApply={handleDateApply}
                    onErrorChange={onDateErrorChange}
                    showError={false}
                    variant="inline"
                />
            )}
            {onRefresh && (
                <button
                    type="button"
                    className="date-filter-bar__refresh"
                    onClick={onRefresh}
                    disabled={refreshDisabled}
                >
                    {refreshLoading ? '🔄' : '🔄'} {refreshLabel}
                </button>
            )}
        </div>
    );
};

export default DateFilterBar;
