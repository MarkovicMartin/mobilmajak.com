import React, { useState, useEffect, useCallback, useMemo } from 'react';
import DatePicker, { registerLocale } from 'react-datepicker';
import { cs } from 'date-fns/locale';
import { format, parseISO, isValid } from 'date-fns';
import {
    isValidISODate,
    normalizeDateRange,
    INVALID_DATE_MESSAGE,
} from '../utils/analyticsDateRange';
import 'react-datepicker/dist/react-datepicker.css';
import './AnalyticsDatePicker.css';

registerLocale('cs', cs);

/**
 * Rozsah Od/Do s draft stavem – API / rodič se aktualizuje až po blur nebo Enter.
 */
const AnalyticsDateRange = ({
    startDate = '',
    endDate = '',
    onApply,
    onErrorChange,
    showError = true,
    errorClassName = 'error-container',
    errorStyle,
    variant = 'filter-group',
    inputClassName = '',
    startLabel = 'Od:',
    endLabel = 'Do:',
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

    const applyDates = useCallback(() => {
        const normalized = normalizeDateRange(dateDraft.start_date, dateDraft.end_date);
        if (!normalized) {
            reportError(INVALID_DATE_MESSAGE);
            return;
        }
        reportError('');
        setDateDraft(normalized);
        if (onApply) onApply(normalized);
    }, [dateDraft, onApply, reportError]);

    const onDraftChange = (field, value) => {
        setDateDraft((prev) => ({ ...prev, [field]: value }));
        reportError('');
    };

    const onKeyDown = (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            applyDates();
        }
    };

    const startInput = (
        <input
            type="date"
            className={inputClassName || undefined}
            value={dateDraft.start_date}
            max={dateDraft.end_date || undefined}
            onChange={(e) => onDraftChange('start_date', e.target.value)}
            onBlur={applyDates}
            onKeyDown={onKeyDown}
        />
    );

    const endInput = (
        <input
            type="date"
            className={inputClassName || undefined}
            value={dateDraft.end_date}
            min={dateDraft.start_date || undefined}
            onChange={(e) => onDraftChange('end_date', e.target.value)}
            onBlur={applyDates}
            onKeyDown={onKeyDown}
        />
    );

    const errorEl = showError && dateError ? (
        <div className={errorClassName} style={errorStyle}>{dateError}</div>
    ) : null;

    if (variant === 'inline') {
        return (
            <>
                <div className="date-inputs">
                    {startInput}
                    <span>až</span>
                    {endInput}
                </div>
                {errorEl}
            </>
        );
    }

    if (variant === 'bare') {
        return (
            <>
                {startInput}
                {endInput}
                {errorEl}
            </>
        );
    }

    return (
        <>
            <div className="filter-group">
                <label>{startLabel}</label>
                {startInput}
            </div>
            <div className="filter-group">
                <label>{endLabel}</label>
                {endInput}
            </div>
            {errorEl}
        </>
    );
};

export default AnalyticsDateRange;

/** Jedno datum – draft; s highlightDates použije react-datepicker. */
export const AnalyticsDateInput = ({
    value = '',
    onApply,
    onErrorChange,
    label,
    id,
    showError = true,
    errorClassName = 'error-container',
    inputClassName = '',
    wrapperClassName = 'filter-group',
    required = false,
    highlightDates = [],
    onMonthChange,
    isClearable = true,
}) => {
    const [draft, setDraft] = useState(value);
    const [dateError, setDateError] = useState('');

    const highlightSet = useMemo(() => new Set(highlightDates), [highlightDates]);
    const useCalendarPicker = onMonthChange != null || highlightDates.length > 0;

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

    const applyDate = useCallback(() => {
        if (!draft) {
            reportError('');
            if (onApply && draft !== value) onApply('');
            return;
        }
        if (!isValidISODate(draft)) {
            reportError(INVALID_DATE_MESSAGE);
            return;
        }
        reportError('');
        if (onApply && draft !== value) onApply(draft);
    }, [draft, value, onApply, reportError]);

    const onKeyDown = (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            applyDate();
        }
    };

    const handlePickerChange = (picked) => {
        const iso = picked ? format(picked, 'yyyy-MM-dd') : '';
        setDraft(iso);
        reportError('');
        if (onApply) onApply(iso);
    };

    const dayClassName = (d) => {
        const iso = format(d, 'yyyy-MM-dd');
        return highlightSet.has(iso) ? 'analytics-day-has-data' : undefined;
    };

    const selectedDate = draft && isValidISODate(draft) ? parseISO(draft) : null;
    const pickerSelected = selectedDate && isValid(selectedDate) ? selectedDate : null;

    const input = useCalendarPicker ? (
        <DatePicker
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
            dayClassName={dayClassName}
            dateFormat="dd.MM.yyyy"
            locale="cs"
            placeholderText="dd.mm.rrrr"
            className={`analytics-date-picker-input ${inputClassName || ''}`.trim()}
            isClearable={isClearable}
            required={required}
            showPopperArrow={false}
        />
    ) : (
        <input
            type="date"
            id={id}
            className={inputClassName || undefined}
            value={draft}
            required={required}
            onChange={(e) => {
                setDraft(e.target.value);
                reportError('');
            }}
            onBlur={applyDate}
            onKeyDown={onKeyDown}
        />
    );

    if (!label) {
        return (
            <>
                {input}
                {showError && dateError && (
                    <div className={errorClassName}>{dateError}</div>
                )}
            </>
        );
    }

    return (
        <div className={wrapperClassName}>
            <label htmlFor={id}>{label}</label>
            {input}
            {showError && dateError && (
                <div className={errorClassName}>{dateError}</div>
            )}
        </div>
    );
};

export { isValidISODate, normalizeDateRange, INVALID_DATE_MESSAGE };
