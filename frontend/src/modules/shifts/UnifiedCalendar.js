import React, { useMemo, useRef, useEffect, useCallback } from 'react';
import { format, parse, startOfMonth, startOfWeek, addDays } from 'date-fns';
import { cs } from 'date-fns/locale';
import './UnifiedCalendar.css';

/**
 * Unified calendar grid used in both "Správa směn" (full) and "Hromadně" (compact) views.
 * Always renders a 7 x 6 grid (42 cells). Week starts on Monday.
 *
 * onDateClick – jeden klik bez tažení
 * onDateDragSelect – při tažení (toggle výběru)
 */
function UnifiedCalendar({
  month, // 'YYYY-MM'
  variant = 'full', // 'full' | 'compact'
  selectedDates = new Set(), // Set<string> of 'yyyy-MM-dd'
  onDateClick,
  onDateDragSelect,
  enableDragSelect = false,
  renderCellContent, // (date: Date, meta: { isCurrentMonth, isToday, isSelected }) => ReactNode
  isDateEnabled, // optional (date: Date) => boolean
  getExtraCellClass, // optional (dateStr: string) => string
}) {
  const monthDate = useMemo(() => parse(`${month}-01`, 'yyyy-MM-dd', new Date()), [month]);

  const firstOfMonth = startOfMonth(monthDate);
  const gridStart = startOfWeek(firstOfMonth, { weekStartsOn: 1, locale: cs });
  const days = useMemo(() => {
    const cells = [];
    for (let i = 0; i < 42; i += 1) {
      cells.push(addDays(gridStart, i));
    }
    return cells;
  }, [gridStart]);

  const daysByStr = useMemo(() => {
    const map = new Map();
    days.forEach((d) => map.set(format(d, 'yyyy-MM-dd'), d));
    return map;
  }, [days]);

  const todayStr = format(new Date(), 'yyyy-MM-dd');
  const isEnabled = useCallback(
    (date) => (isDateEnabled ? isDateEnabled(date) : true),
    [isDateEnabled],
  );

  const headerDays = useMemo(() => {
    const start = startOfWeek(new Date(), { weekStartsOn: 1, locale: cs });
    return Array.from({ length: 7 }, (_, i) => addDays(start, i));
  }, []);

  const cellRefs = useRef([]);
  const dragState = useRef({ active: false, moved: false, startDateStr: null, mode: 'add' });

  const isCellDisabled = useCallback((dateStr, date) => {
    const inCurrentMonth = format(date, 'yyyy-MM') === month;
    return !inCurrentMonth || !isEnabled(date);
  }, [month, isEnabled]);

  const applyDragSelect = useCallback((dateStr, date, mode) => {
    if (!onDateDragSelect || isCellDisabled(dateStr, date)) return;
    const isSelected = selectedDates && selectedDates.has(dateStr);
    if (mode === 'add' && !isSelected) {
      onDateDragSelect(dateStr, date);
    } else if (mode === 'remove' && isSelected) {
      onDateDragSelect(dateStr, date);
    }
  }, [onDateDragSelect, selectedDates, isCellDisabled]);

  useEffect(() => {
    const endDrag = () => {
      const st = dragState.current;
      if (st.active && !st.moved && st.startDateStr && onDateClick) {
        const date = daysByStr.get(st.startDateStr);
        if (date && !isCellDisabled(st.startDateStr, date)) {
          onDateClick(st.startDateStr, date);
        }
      }
      dragState.current = { active: false, moved: false, startDateStr: null, mode: 'add' };
    };
    document.addEventListener('mouseup', endDrag);
    return () => document.removeEventListener('mouseup', endDrag);
  }, [onDateClick, daysByStr, isCellDisabled]);

  const handleDateMouseDown = (dateStr, date, e) => {
    if (e.button !== 0) return;
    if (isCellDisabled(dateStr, date)) return;
    if (!onDateClick && !onDateDragSelect) return;
    e.preventDefault();

    if (enableDragSelect && onDateDragSelect) {
      const mode = selectedDates.has(dateStr) ? 'remove' : 'add';
      dragState.current = { active: true, moved: false, startDateStr: dateStr, mode };
      return;
    }

    if (onDateClick) {
      onDateClick(dateStr, date);
    }
  };

  const handleDateMouseEnter = (dateStr, date) => {
    if (!enableDragSelect || !dragState.current.active || !onDateDragSelect) return;
    const st = dragState.current;
    if (!st.moved && dateStr !== st.startDateStr) {
      st.moved = true;
      const startDate = daysByStr.get(st.startDateStr);
      if (startDate) applyDragSelect(st.startDateStr, startDate, st.mode);
    }
    if (st.moved) {
      applyDragSelect(dateStr, date, st.mode);
    }
  };

  const handleKeyDown = (idx, e) => {
    if (!['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', 'Enter', ' '].includes(e.key)) return;
    if (['Enter', ' '].includes(e.key)) {
      e.preventDefault();
      const date = days[idx];
      const dateStr = format(date, 'yyyy-MM-dd');
      if (!isCellDisabled(dateStr, date) && onDateClick) onDateClick(dateStr, date);
      return;
    }
    e.preventDefault();
    let next = idx;
    if (e.key === 'ArrowLeft') next = Math.max(0, idx - 1);
    if (e.key === 'ArrowRight') next = Math.min(41, idx + 1);
    if (e.key === 'ArrowUp') next = Math.max(0, idx - 7);
    if (e.key === 'ArrowDown') next = Math.min(41, idx + 7);
    const el = cellRefs.current[next];
    if (el) el.focus();
  };

  const selectable = Boolean(onDateClick || onDateDragSelect);

  return (
    <div
      className={`unified-calendar ${variant}${selectable ? ' unified-calendar--selectable' : ''}`}
      role="grid"
      aria-readonly={!selectable}
    >
      <div className="uc-header" role="row">
        {headerDays.map((d, i) => (
          <div key={i} className="uc-day-name" role="columnheader">
            {format(d, 'EE', { locale: cs }).toUpperCase()}
          </div>
        ))}
      </div>

      <div className="uc-grid">
        {days.map((date, idx) => {
          const dateStr = format(date, 'yyyy-MM-dd');
          const inCurrentMonth = format(date, 'yyyy-MM') === month;
          const isToday = dateStr === todayStr;
          const isSelected = selectedDates && selectedDates.has(dateStr);
          const disabled = isCellDisabled(dateStr, date);
          const extraClass = getExtraCellClass ? getExtraCellClass(dateStr) : '';

          return (
            <div
              key={dateStr + idx}
              ref={(el) => { cellRefs.current[idx] = el; }}
              className={[
                'uc-cell',
                inCurrentMonth ? 'current' : 'other',
                disabled ? 'disabled' : '',
                isSelected ? 'selected' : '',
                isToday ? 'today' : '',
                selectable && !disabled ? 'selectable' : '',
                extraClass || '',
              ].filter(Boolean).join(' ')}
              role="gridcell"
              tabIndex={disabled ? -1 : 0}
              aria-selected={isSelected || undefined}
              onKeyDown={(e) => handleKeyDown(idx, e)}
              onMouseDown={(e) => handleDateMouseDown(dateStr, date, e)}
              onMouseEnter={() => handleDateMouseEnter(dateStr, date)}
            >
              <div className="uc-day-number">{format(date, 'd')}</div>
              <div className="uc-cell-content">
                {renderCellContent ? renderCellContent(date, { isCurrentMonth: inCurrentMonth, isToday, isSelected }) : null}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default UnifiedCalendar;
