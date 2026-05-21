import React, { useMemo, useRef } from 'react';
import { format, parse, startOfMonth, startOfWeek, addDays } from 'date-fns';
import { cs } from 'date-fns/locale';
import './UnifiedCalendar.css';

/**
 * Unified calendar grid used in both "Správa směn" (full) and "Hromadně" (compact) views.
 * Always renders a 7 x 6 grid (42 cells). Week starts on Monday.
 */
function UnifiedCalendar({
  month, // 'YYYY-MM'
  variant = 'full', // 'full' | 'compact'
  selectedDates = new Set(), // Set<string> of 'yyyy-MM-dd'
  onDateClick,
  renderCellContent, // (date: Date, meta: { isCurrentMonth, isToday, isSelected }) => ReactNode
  isDateEnabled, // optional (date: Date) => boolean
  getExtraCellClass, // optional (dateStr: string) => string
}) {
  const monthDate = useMemo(() => parse(`${month}-01`, 'yyyy-MM-dd', new Date()), [month]);

  // Compute start Monday and ensure 42 cells
  const firstOfMonth = startOfMonth(monthDate);
  const gridStart = startOfWeek(firstOfMonth, { weekStartsOn: 1, locale: cs });
  // Always 42 cells (6 weeks)
  const days = useMemo(() => {
    const cells = [];
    for (let i = 0; i < 42; i += 1) {
      cells.push(addDays(gridStart, i));
    }
    return cells;
  }, [gridStart]);

  const todayStr = format(new Date(), 'yyyy-MM-dd');
  const isEnabled = (date) => (isDateEnabled ? isDateEnabled(date) : true);

  const headerDays = useMemo(() => {
    const start = startOfWeek(new Date(), { weekStartsOn: 1, locale: cs });
    return Array.from({ length: 7 }, (_, i) => addDays(start, i));
  }, []);

  const cellRefs = useRef([]);

  const handleKeyDown = (idx, e) => {
    if (!['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(e.key)) return;
    e.preventDefault();
    let next = idx;
    if (e.key === 'ArrowLeft') next = Math.max(0, idx - 1);
    if (e.key === 'ArrowRight') next = Math.min(41, idx + 1);
    if (e.key === 'ArrowUp') next = Math.max(0, idx - 7);
    if (e.key === 'ArrowDown') next = Math.min(41, idx + 7);
    const el = cellRefs.current[next];
    if (el) el.focus();
  };

  return (
    <div className={`unified-calendar ${variant}`} role="grid" aria-readonly>
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
          const disabled = !inCurrentMonth || !isEnabled(date);
          const extraClass = getExtraCellClass ? getExtraCellClass(dateStr) : '';

          return (
            <div
              key={dateStr + idx}
              ref={(el) => (cellRefs.current[idx] = el)}
              className={[
                'uc-cell',
                inCurrentMonth ? 'current' : 'other',
                disabled ? 'disabled' : '',
                isSelected ? 'selected' : '',
                isToday ? 'today' : '',
                extraClass || '',
              ].join(' ')}
              role="gridcell"
              tabIndex={0}
              aria-selected={isSelected || undefined}
              onKeyDown={(e) => handleKeyDown(idx, e)}
              onClick={() => {
                if (disabled) return;
                onDateClick && onDateClick(dateStr, date);
              }}
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


