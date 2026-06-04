import React, { useState, useEffect, useCallback } from 'react';
import { format, addMonths, subMonths } from 'date-fns';
import { cs } from 'date-fns/locale';
import { Link } from 'react-router-dom';
import api from '../../services/api';
import { taskAPI } from '../../services/api';
import UnifiedCalendar from '../shifts/UnifiedCalendar';
import { urgencyClassName, urgencyForTask } from '../../utils/taskUrgency';
import '../tasks/TasksModule.css';

const ProfileCalendar = () => {
    const [month, setMonth] = useState(() => format(new Date(), 'yyyy-MM'));
    const [shiftData, setShiftData] = useState({});
    const [taskData, setTaskData] = useState({});
    const [loading, setLoading] = useState(false);

    const load = useCallback(async () => {
        setLoading(true);
        try {
            const [shiftsRes, tasksRes] = await Promise.all([
                api.get('/shifts/calendar/', { params: { mesic: month, scope: 'mine' } }),
                taskAPI.getCalendar(month),
            ]);
            setShiftData(shiftsRes.data?.kalendar_data || {});
            setTaskData(tasksRes.kalendar_data || tasksRes?.data?.kalendar_data || {});
        } catch {
            setShiftData({});
            setTaskData({});
        } finally {
            setLoading(false);
        }
    }, [month]);

    useEffect(() => {
        load();
    }, [load]);

    const renderCell = (_date, { isCurrentMonth }) => {
        if (!isCurrentMonth) return null;
        const dateStr = format(_date, 'yyyy-MM-dd');
        const shifts = shiftData[dateStr] || [];
        const tasks = taskData[dateStr] || [];
        return (
            <>
                {shifts.slice(0, 2).map((s) => (
                    <div
                        key={`s-${s.id}`}
                        className="uc-shift-chip"
                        title={`${s.prodejna_nazev}: ${s.cas_od}–${s.cas_do}`}
                    >
                        {s.cas_od} {s.prodejna_nazev?.slice(0, 8)}
                    </div>
                ))}
                {tasks.slice(0, 2).map((t) => (
                    <div
                        key={`t-${t.id}`}
                        className={`uc-task-chip ${urgencyClassName(urgencyForTask(t))}`}
                        title={t.ukol}
                    >
                        {t.ukol?.slice(0, 12)}
                    </div>
                ))}
            </>
        );
    };

    return (
        <div className="profile-calendar">
            <div className="profile-calendar-legend">
                <span><span className="legend-dot legend-dot--shift" /> Směna</span>
                <span><span className="legend-dot legend-dot--task" /> Úkol</span>
            </div>
            <div className="calendar-header" style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '0.75rem' }}>
                <button
                    type="button"
                    className="btn-outline"
                    onClick={() => setMonth(format(subMonths(new Date(`${month}-01`), 1), 'yyyy-MM'))}
                >
                    ‹
                </button>
                <strong>{format(new Date(`${month}-01`), 'LLLL yyyy', { locale: cs })}</strong>
                <button
                    type="button"
                    className="btn-outline"
                    onClick={() => setMonth(format(addMonths(new Date(`${month}-01`), 1), 'yyyy-MM'))}
                >
                    ›
                </button>
                {loading && <span className="muted">Načítám…</span>}
            </div>
            <UnifiedCalendar month={month} variant="full" renderCellContent={renderCell} />
            <p className="profile-calendar-link">
                <Link to="/shifts">Upravit směny v modulu Směny →</Link>
            </p>
        </div>
    );
};

export default ProfileCalendar;
