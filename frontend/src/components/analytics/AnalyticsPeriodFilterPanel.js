import React from 'react';
import CustomDropdown from '../CustomDropdown';
import AnalyticsDateRange from '../AnalyticsDateRange';
import PeriodSegmentBar from '../PeriodSegmentBar';
import { buildAnalyticsMonthFilterOptions } from '../../utils/analyticsMonthOptions';
import { QUICK_RANGE_PRESETS } from '../../utils/analyticsQuickRange';
import '../../modules/analytics/sections/CelkovaCisla.css';

/**
 * Sjednocený filtr období – stejné rozložení jako Celková čísla.
 * Řádek 1: Období, Datum (custom), doplňkové filtry, Obnovit
 * Řádek 2: rychlé presety (jen při vlastním období)
 */
const AnalyticsPeriodFilterPanel = ({
    filters,
    quickKey,
    onPeriodChange,
    onDateApply,
    onQuickPreset,
    onRefresh,
    onDateErrorChange,
    loading = false,
    dateError = '',
    refreshLabel = 'Obnovit',
    className = '',
    children,
}) => {
    const isCustom = filters.period === 'custom';
    const periodValue =
        filters.period === 'monthly_select' && filters.selected_month
            ? `month:${filters.selected_month}`
            : 'custom';

    const handlePeriodDropdown = (selectedValue) => {
        if (selectedValue === 'custom') {
            onPeriodChange?.({ type: 'custom' });
        } else if (selectedValue.startsWith('month:')) {
            onPeriodChange?.({ type: 'month', month: selectedValue.split(':')[1] });
        }
    };

    return (
        <div className={`celkova-cisla-filters ${className}`.trim()}>
            <div className="filter-row filter-row--primary">
                <div className="filter-group">
                    <label>Období:</label>
                    <CustomDropdown
                        options={buildAnalyticsMonthFilterOptions()}
                        value={periodValue}
                        placeholder="Vyberte období"
                        onChange={handlePeriodDropdown}
                    />
                </div>

                {isCustom && (
                    <div className="filter-group filter-group--date-range">
                        <label>Datum:</label>
                        <AnalyticsDateRange
                            startDate={filters.start_date}
                            endDate={filters.end_date}
                            onApply={onDateApply}
                            onErrorChange={onDateErrorChange || (() => {})}
                            showError={false}
                            variant="inline"
                        />
                    </div>
                )}

                {children}

                <div className="filter-group refresh-group">
                    <label aria-hidden="true">&nbsp;</label>
                    <button
                        type="button"
                        className="refresh-btn main-refresh"
                        onClick={onRefresh}
                        disabled={loading || !!dateError}
                    >
                        🔄 {refreshLabel}
                    </button>
                </div>
            </div>

            {isCustom && (
                <div className="filter-row filter-row--presets">
                    <PeriodSegmentBar
                        options={QUICK_RANGE_PRESETS}
                        value={quickKey === 'custom' ? null : quickKey}
                        onChange={onQuickPreset}
                        ariaLabel="Rychlé volby období"
                    />
                </div>
            )}

            {dateError && (
                <div className="celkova-cisla-error celkova-cisla-filters__error">{dateError}</div>
            )}
        </div>
    );
};

export default AnalyticsPeriodFilterPanel;
