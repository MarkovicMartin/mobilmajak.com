import React, { useState, useEffect, useCallback } from 'react';
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

const DEFAULT_INPUT_CLASS = 'analytics-date-picker-input';

const isoFromDate = (d) => format(d, 'yyyy-MM-dd');

const dateFromIso = (iso) => {
    if (!iso || !isValidISODate(iso)) return null;
    const parsed = parseISO(iso);
    return isValid(parsed) ? parsed : null;
};

const AnalyticsDatePickerField = ({
    id,
    selectedIso,
    onChange,
    minDate,
    maxDate,
    inputClassName,
    placeholderText = 'dd.mm.rrrr',
}) => (
    <DatePicker
        id={id}
        selected={dateFromIso(selectedIso)}
        onChange={(picked) => onChange(picked ? isoFromDate(picked) : '')}
        minDate={minDate ? dateFromIso(minDate) : undefined}
        maxDate={maxDate ? dateFromIso(maxDate) : undefined}
        dateFormat="dd.MM.yyyy"
        locale="cs"
        placeholderText={placeholderText}
        className={`${DEFAULT_INPUT_CLASS} ${inputClassName || ''}`.trim()}
        isClearable
        showPopperArrow={false}
    />
);

/**
 * Rozsah Od/Do – kalendář jako u profilu / úkolů (react-datepicker).
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
            if (onApply) onApply(normalized);
        },
        [dateDraft, onApply, reportError]
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
        <AnalyticsDatePickerField
            id="analytics-range-start"
            selectedIso={dateDraft.start_date}
            onChange={(v) => onFieldChange('start_date', v)}
            maxDate={dateDraft.end_date || undefined}
            inputClassName={pickerClass}
            placeholderText="Od"
        />
    );

    const endPicker = (
        <AnalyticsDatePickerField
            id="analytics-range-end"
            selectedIso={dateDraft.end_date}
            onChange={(v) => onFieldChange('end_date', v)}
            minDate={dateDraft.start_date || undefined}
            inputClassName={pickerClass}
            placeholderText="Do"
        />
    );

    const errorEl = showError && dateError ? (
        <div className={errorClassName} style={errorStyle}>{dateError}</div>
    ) : null;

    if (variant === 'inline') {
        return (
            <div className="analytics-date-range analytics-date-range--inline">
                <div className="date-inputs">
                    {startPicker}
                    <span className="analytics-date-range-sep">až</span>
                    {endPicker}
                </div>
                {errorEl}
            </div>
        );
    }

    if (variant === 'bare') {
        return (
            <div className="analytics-date-range analytics-date-range--bare">
                {startPicker}
                {endPicker}
                {errorEl}
            </div>
        );
    }

    return (
        <div className="analytics-date-range">
            <div className="filter-group">
                <label htmlFor="analytics-range-start">{startLabel}</label>
                {startPicker}
            </div>
            <div className="filter-group">
                <label htmlFor="analytics-range-end">{endLabel}</label>
                {endPicker}
            </div>
            {errorEl}
        </div>
    );
};

export default AnalyticsDateRange;

/** Jedno datum – kalendář (react-datepicker). */
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

    const highlightSet = React.useMemo(() => new Set(highlightDates), [highlightDates]);

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
        if (onApply) onApply(iso);
    };

    const dayClassName = (d) => {
        const iso = format(d, 'yyyy-MM-dd');
        return highlightSet.has(iso) ? 'analytics-day-has-data' : undefined;
    };

    const pickerSelected = dateFromIso(draft);

    const input = (
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
            dayClassName={highlightDates.length ? dayClassName : undefined}
            dateFormat="dd.MM.yyyy"
            locale="cs"
            placeholderText="dd.mm.rrrr"
            className={`${DEFAULT_INPUT_CLASS} ${inputClassName || ''}`.trim()}
            isClearable={isClearable}
            required={required}
            showPopperArrow={false}
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
