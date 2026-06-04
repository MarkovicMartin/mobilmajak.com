import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
    PERIOD_OPTIONS,
    filterAttendanceEntries,
    resolveFetchMonths,
    periodSummaryLabel,
} from './attendanceLogFilters';
import './AttendanceLogPanel.css';

function AttendanceLogPanel({ month }) {
    const [entries, setEntries] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [filterProblems, setFilterProblems] = useState(false);
    const [period, setPeriod] = useState('uplynule');

    const loadLog = useCallback(async () => {
        const months = resolveFetchMonths(period, month);
        if (!months.length) return;

        setLoading(true);
        setError('');
        try {
            const responses = await Promise.all(
                months.map(async (mesic) => {
                    const res = await fetch(`/api/shifts/attendance/log/?mesic=${mesic}`, {
                        credentials: 'include',
                    });
                    if (!res.ok) {
                        const data = await res.json().catch(() => ({}));
                        throw new Error(data.error || 'Chyba při načítání logu');
                    }
                    return res.json();
                })
            );

            const byShift = new Map();
            responses.forEach((data) => {
                (data.entries || []).forEach((entry) => {
                    byShift.set(entry.smena_id, entry);
                });
            });
            setEntries([...byShift.values()]);
        } catch (e) {
            setError(e.message);
            setEntries([]);
        } finally {
            setLoading(false);
        }
    }, [period, month]);

    useEffect(() => {
        loadLog();
    }, [loadLog]);

    const periodRows = useMemo(
        () => filterAttendanceEntries(entries, period),
        [entries, period]
    );

    const displayed = useMemo(() => (
        filterProblems ? periodRows.filter((e) => e.problem) : periodRows
    ), [periodRows, filterProblems]);

    const problemyCount = useMemo(
        () => periodRows.filter((e) => e.problem).length,
        [periodRows]
    );

    const formatDate = (iso) => {
        if (!iso) return '';
        const [y, m, d] = iso.split('-');
        return `${d}.${m}.${y}`;
    };

    if (loading) {
        return <div className="attendance-log loading">Načítání logu docházky…</div>;
    }

    return (
        <div className="attendance-log">
            <div className="attendance-log-periods">
                {PERIOD_OPTIONS.map((opt) => (
                    <button
                        key={opt.id}
                        type="button"
                        className={period === opt.id ? 'active' : ''}
                        onClick={() => setPeriod(opt.id)}
                    >
                        {opt.label}
                    </button>
                ))}
            </div>

            <div className="attendance-log-toolbar">
                <span className="attendance-log-summary">
                    {periodSummaryLabel(period)} · <strong>{displayed.length}</strong> směn
                </span>
                <span className="problemy-badge">
                    Problémů: <strong>{problemyCount}</strong>
                </span>
                <label>
                    <input
                        type="checkbox"
                        checked={filterProblems}
                        onChange={(e) => setFilterProblems(e.target.checked)}
                    />
                    Jen problémy
                </label>
                <button type="button" className="btn-secondary-sm" onClick={loadLog}>
                    Obnovit
                </button>
            </div>

            {error && <div className="error-message">{error}</div>}

            <div className="attendance-log-table-wrap">
                <table className="attendance-log-table">
                    <thead>
                        <tr>
                            <th>Jméno</th>
                            <th>Datum</th>
                            <th>Prodejna</th>
                            <th>Plán</th>
                            <th>Docházka</th>
                            <th>Stav</th>
                            <th>Hodiny</th>
                        </tr>
                    </thead>
                    <tbody>
                        {displayed.length === 0 ? (
                            <tr>
                                <td colSpan={7} className="empty">Žádné záznamy pro zvolené období</td>
                            </tr>
                        ) : (
                            displayed.map((e) => (
                                <tr key={e.smena_id} className={e.problem ? 'row-problem' : ''}>
                                    <td>{e.jmeno}</td>
                                    <td>{formatDate(e.datum)}</td>
                                    <td>{e.prodejna}</td>
                                    <td>{e.plan_od} – {e.plan_do}</td>
                                    <td>{e.cas_rozsah_od} – {e.cas_rozsah_do}</td>
                                    <td>
                                        {e.stav}
                                        {e.problem && (
                                            <span className="problem-tag" title={e.problem_duvod}> ⚠</span>
                                        )}
                                    </td>
                                    <td>{e.hodiny_z_dochozky}</td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

export default AttendanceLogPanel;
