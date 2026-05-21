import React, { useState, useEffect, useCallback } from 'react';
import './AttendanceLogPanel.css';

function AttendanceLogPanel({ month }) {
    const [entries, setEntries] = useState([]);
    const [problemyCount, setProblemyCount] = useState(0);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [filterProblems, setFilterProblems] = useState(false);

    const loadLog = useCallback(async () => {
        if (!month) return;
        setLoading(true);
        setError('');
        try {
            const res = await fetch(`/api/shifts/attendance/log/?mesic=${month}`, { credentials: 'include' });
            if (!res.ok) {
                const data = await res.json().catch(() => ({}));
                throw new Error(data.error || 'Chyba při načítání logu');
            }
            const data = await res.json();
            setEntries(data.entries || []);
            setProblemyCount(data.problemy_count || 0);
        } catch (e) {
            setError(e.message);
            setEntries([]);
        } finally {
            setLoading(false);
        }
    }, [month]);

    useEffect(() => {
        loadLog();
    }, [loadLog]);

    const displayed = filterProblems
        ? entries.filter((e) => e.problem)
        : entries;

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
            <div className="attendance-log-toolbar">
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
                                <td colSpan={7} className="empty">Žádné záznamy</td>
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
