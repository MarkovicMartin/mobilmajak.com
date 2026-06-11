import React, { useState, useEffect, useCallback } from 'react';
import DatePickerLib from 'react-datepicker';
import {
    normalizeDateRange,
    INVALID_DATE_MESSAGE,
} from '../../utils/analyticsDateRange';
import { UI_DATE_INPUT_CLASS, isoFromDate, dateFromIso } from './dateUtils';
import './DatePicker.css';
import './DateRangePicker.css';

const DateRangeField = ({
    id,
    selectedIso,
    onChange,
    minDate,
    maxDate,
    inputClassName,
    placeholderText,
    legacy,
}) => (
    <DatePickerLib
        id={id}
        selected={dateFromIso(selectedIso)}
        onChange={(picked) => onChange(picked ? isoFromDate(picked) : '')}
        minDate={minDate ? dateFromIso(minDate) : undefined}
        maxDate={maxDate ? dateFromIso(maxDate) : undefined}
        dateFormat="dd.MM.yyyy"
        locale="cs"
        placeholderText={placeholderText}
        className={
            legacy
                ? `analytics-date-picker-input ${inputClassName || ''}`.trim()
                : `${UI_DATE_INPUT_CLASS} input ${inputClassName || ''}`.trim()
        }
        isClearable
        showPopperArrow={false}
        popperClassName="ui-date-picker__popper"
    />
);

/**
 * Rozsah Od/Do – ISO yyyy-MM-dd, auto-apply při vyplnění obou polí.
 */
const DateRangePicker = ({
    startDate = '',
    endDate = '',
    onApply,
    onChange,
    onErrorChange,
    showError = true,
    errorClassName = 'form-v2__error',
    errorStyle,
    variant = 'labeled',
    inputClassName = '',
    startLabel = 'Od:',
    endLabel = 'Do:',
    legacy = false,
}) => {
    const [dateDraft, setDateDraft] = useState({
        start_date: startDate,
        end_date: endDate,
    });
    const [dateError, setDateError] = useState('');

    useEffect(() => {
        setDateDraft({ start_date: startDate, end_date: endDate });
    }, [startDate, endDate]);

    const reportError = useCallback(
        (msg) => {
            setDateError(msg);
            if (onErrorChange) onErrorChange(msg);
        },
        [onErrorChange]
    );

    const applyDates = useCallback(
        (nextDraft) => {
            const draft = nextDraft || dateDraft;
            const normalized = normalizeDateRange(draft.start_date, draft.end_date);
            if (!normalized) {
                reportError(INVALID_DATE_MESSAGE);
                return;
            }
            reportError('');
            setDateDraft(normalized);
            if (onChange) onChange(normalized);
            if (onApply) onApply(normalized);
        },
        [dateDraft, onApply, onChange, reportError]
    );

    const onFieldChange = (field, value) => {
        const next = { ...dateDraft, [field]: value };
        setDateDraft(next);
        reportError('');
        if (next.start_date && next.end_date) {
            const normalized = normalizeDateRange(next.start_date, next.end_date);
            if (normalized) applyDates(normalized);
        }
    };

    const pickerClass = inputClassName || '';

    const startPicker = (
        <DateRangeField
            id="ui-date-range-start"
            selectedIso={dateDraft.start_date}
            onChange={(v) => onFieldChange('start_date', v)}
            maxDate={dateDraft.end_date || undefined}
            inputClassName={pickerClass}
            placeholderText="Od"
            legacy={legacy}
        />
    );

    const endPicker = (
        <DateRangeField
            id="ui-date-range-end"
            selectedIso={dateDraft.end_date}
            onChange={(v) => onFieldChange('end_date', v)}
            minDate={dateDraft.start_date || undefined}
            inputClassName={pickerClass}
            placeholderText="Do"
            legacy={legacy}
        />
    );

    const errorEl = showError && dateError ? (
        <div className={errorClassName} style={errorStyle}>
            {dateError}
        </div>
    ) : null;

    const rootClass = legacy ? 'analytics-date-range' : 'ui-date-range';

    if (variant === 'inline') {
        return (
            <div className={`${rootClass} ${rootClass}--inline`}>
                <div className={legacy ? 'date-inputs' : 'ui-date-range__inputs'}>
                    {startPicker}
                    <span className={legacy ? 'analytics-date-range-sep' : 'ui-date-range__sep'}>
                        až
                    </span>
                    {endPicker}
                </div>
                {errorEl}
            </div>
        );
    }

    if (variant === 'bare') {
        return (
            <div className={`${rootClass} ${rootClass}--bare`}>
                {startPicker}
                {endPicker}
                {errorEl}
            </div>
        );
    }

    const groupClass = legacy ? 'filter-group' : 'form-v2__field';

    return (
        <div className={rootClass}>
            <div className={groupClass}>
                <label htmlFor="ui-date-range-start" className={legacy ? undefined : 'label'}>
                    {startLabel}
                </label>
                {startPicker}
            </div>
            <div className={groupClass}>
                <label htmlFor="ui-date-range-end" className={legacy ? undefined : 'label'}>
                    {endLabel}
                </label>
                {endPicker}
            </div>
            {errorEl}
        </div>
    );
};

export default DateRangePicker;
