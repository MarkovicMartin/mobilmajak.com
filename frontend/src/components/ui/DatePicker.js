import React, { useState, useEffect, useCallback, useMemo } from 'react';
import DatePickerLib from 'react-datepicker';
import { format } from 'date-fns';
import { UI_DATE_INPUT_CLASS, dateFromIso } from './dateUtils';
import './DatePicker.css';

/**
 * Jedno datum – react-datepicker, ISO yyyy-MM-dd.
 */
const DatePicker = ({
    value = '',
    onChange,
    onApply,
    onErrorChange,
    label,
    id,
    showError = true,
    errorClassName = 'form-v2__error',
    inputClassName = '',
    wrapperClassName = 'form-v2__field',
    required = false,
    highlightDates = [],
    onMonthChange,
    isClearable = true,
    minDate,
    maxDate,
    placeholderText = 'dd.mm.rrrr',
    legacy = false,
}) => {
    const [draft, setDraft] = useState(value);
    const [dateError, setDateError] = useState('');

    const highlightSet = useMemo(() => new Set(highlightDates), [highlightDates]);

    useEffect(() => {
        setDraft(value);
    }, [value]);

    const reportError = useCallback(
        (msg) => {
            setDateError(msg);
            if (onErrorChange) onErrorChange(msg);
        },
        [onErrorChange]
    );

    const handlePickerChange = (picked) => {
        const iso = picked ? format(picked, 'yyyy-MM-dd') : '';
        setDraft(iso);
        reportError('');
        if (onChange) onChange(iso);
        if (onApply) onApply(iso);
    };

    const dayClassName = (d) => {
        const iso = format(d, 'yyyy-MM-dd');
        return highlightSet.has(iso) ? 'ui-date-picker__day-has-data' : undefined;
    };

    const pickerSelected = dateFromIso(draft);
    const inputClass = legacy
        ? `analytics-date-picker-input ${inputClassName}`.trim()
        : `${UI_DATE_INPUT_CLASS} input ${inputClassName}`.trim();

    const input = (
        <DatePickerLib
            id={id}
            selected={pickerSelected}
            onChange={handlePickerChange}
            onMonthChange={(d) => {
                if (onMonthChange) onMonthChange(format(d, 'yyyy-MM'));
            }}
            onCalendarOpen={() => {
                if (onMonthChange && pickerSelected) {
                    onMonthChange(format(pickerSelected, 'yyyy-MM'));
                } else if (onMonthChange) {
                    onMonthChange(format(new Date(), 'yyyy-MM'));
                }
            }}
            dayClassName={highlightDates.length ? dayClassName : undefined}
            minDate={minDate ? dateFromIso(minDate) : undefined}
            maxDate={maxDate ? dateFromIso(maxDate) : undefined}
            dateFormat="dd.MM.yyyy"
            locale="cs"
            placeholderText={placeholderText}
            className={inputClass}
            isClearable={isClearable}
            required={required}
            showPopperArrow={false}
            popperClassName="ui-date-picker__popper"
        />
    );

    const errorEl = showError && dateError ? (
        <div className={errorClassName}>{dateError}</div>
    ) : null;

    if (!label) {
        return (
            <div className="ui-date-picker">
                {input}
                {errorEl}
            </div>
        );
    }

    return (
        <div className={`ui-date-picker ${wrapperClassName}`.trim()}>
            <label htmlFor={id} className="label">
                {label}
            </label>
            {input}
            {errorEl}
        </div>
    );
};

export default DatePicker;
