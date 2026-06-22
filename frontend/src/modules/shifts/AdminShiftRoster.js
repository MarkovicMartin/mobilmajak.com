import React, { useMemo, useState } from 'react';
import { format } from 'date-fns';
import { cs } from 'date-fns/locale';
import { shiftRoleLabel } from './shiftRoleLabels';
import {
    collectMonthWorkShifts,
    groupShiftsByWeek,
    groupWeekByStore,
    isPastWeek,
} from './shiftRosterUtils';

function formatWeekLabel(weekStart, weekEnd) {
    const sameMonth = weekStart.getMonth() === weekEnd.getMonth();
    const from = format(weekStart, sameMonth ? 'd.' : 'd. M.', { locale: cs });
    const to = format(weekEnd, 'd. M. yyyy', { locale: cs });
    return `${from} – ${to}`;
}

function formatTime(value) {
    return value ? String(value).substring(0, 5) : '';
}

function AdminShiftRoster({ kalendarData, stores, month }) {
    const weeks = useMemo(() => {
        const shifts = collectMonthWorkShifts(kalendarData);
        return groupShiftsByWeek(shifts).map((week) => ({
            ...week,
            stores: groupWeekByStore(week.shifts, stores),
        }));
    }, [kalendarData, stores]);

    const [expandedPast, setExpandedPast] = useState(() => new Set());

    if (!weeks.length) {
        return (
            <div className="admin-shift-roster admin-shift-roster--empty">
                <p className="muted">V {month} nejsou naplánované pracovní směny.</p>
            </div>
        );
    }

    const togglePastWeek = (key) => {
        setExpandedPast((prev) => {
            const next = new Set(prev);
            if (next.has(key)) next.delete(key);
            else next.add(key);
            return next;
        });
    };

    return (
        <section className="admin-shift-roster" aria-label="Soupis směn po týdnech">
            <h3 className="admin-shift-roster__title">Soupis směn</h3>
            <p className="admin-shift-roster__hint">
                Přehled po týdnech a prodejnách. Minulé týdny jsou sbalené.
            </p>

            {weeks.map((week) => {
                const weekKey = format(week.weekStart, 'yyyy-MM-dd');
                const past = isPastWeek(week.weekEnd);
                const expanded = !past || expandedPast.has(weekKey);
                const peopleCount = week.stores.reduce((n, s) => n + s.people.length, 0);

                return (
                    <div
                        key={weekKey}
                        className={`admin-shift-roster__week${past ? ' admin-shift-roster__week--past' : ''}`}
                    >
                        {past ? (
                            <button
                                type="button"
                                className="admin-shift-roster__week-toggle"
                                onClick={() => togglePastWeek(weekKey)}
                                aria-expanded={expanded}
                            >
                                <span className="admin-shift-roster__week-chevron" aria-hidden="true">
                                    {expanded ? '▼' : '▶'}
                                </span>
                                <span>
                                    {formatWeekLabel(week.weekStart, week.weekEnd)}
                                    {' · '}
                                    {peopleCount} {peopleCount === 1 ? 'osoba' : peopleCount < 5 ? 'osoby' : 'osob'}
                                    {week.stores.length > 0 && ` · ${week.stores.length} prodejen`}
                                </span>
                            </button>
                        ) : (
                            <h4 className="admin-shift-roster__week-heading">
                                {formatWeekLabel(week.weekStart, week.weekEnd)}
                            </h4>
                        )}

                        {expanded && (
                            <div className="admin-shift-roster__stores">
                                {week.stores.length === 0 ? (
                                    <p className="muted admin-shift-roster__no-stores">Žádné směny v tomto týdnu.</p>
                                ) : (
                                    week.stores.map((store) => (
                                        <div
                                            key={store.prodejna_id}
                                            className="admin-shift-roster__store-tile"
                                            style={{ borderLeftColor: store.prodejna_barva }}
                                        >
                                            <div className="admin-shift-roster__store-head">
                                                {store.prodejna_nazev}
                                            </div>
                                            <ul className="admin-shift-roster__people">
                                                {store.people.map((person) => {
                                                    const role = shiftRoleLabel(person.primary, { short: true });
                                                    const timeLabel = `${formatTime(person.primary.cas_od)}–${formatTime(person.primary.cas_do)}`;
                                                    const daysLabel = person.shiftCount > 1
                                                        ? `${person.shiftCount} dní`
                                                        : null;
                                                    return (
                                                        <li key={person.user_id}>
                                                            <span className="admin-shift-roster__person-name">
                                                                {person.user_jmeno}
                                                            </span>
                                                            <span className="admin-shift-roster__person-meta">
                                                                {[role, timeLabel, daysLabel].filter(Boolean).join(' · ')}
                                                            </span>
                                                        </li>
                                                    );
                                                })}
                                            </ul>
                                        </div>
                                    ))
                                )}
                            </div>
                        )}
                    </div>
                );
            })}
        </section>
    );
}

export default AdminShiftRoster;
