import React, { useState, useEffect, useCallback } from 'react';
import { format, addMonths, subMonths } from 'date-fns';
import { cs } from 'date-fns/locale';
import { useNavigate } from 'react-router-dom';
import api from '../../services/api';
import { taskAPI } from '../../services/api';
import UnifiedCalendar from '../shifts/UnifiedCalendar';
import ProfileDayPanel from './ProfileDayPanel';
import { useAuth } from '../../context/AuthContext';
import { getClosureNotice } from '../../constants/prodejnaZavreni';
import { urgencyClassName, urgencyForTask } from '../../utils/taskUrgency';
import { openTask } from '../../utils/taskNavigation';
import '../shifts/ShiftCalendar.css';
import './ProfileModule.css';

const formatShiftTime = (t) => (t || '').substring(0, 5);

const ProfileCalendar = () => {
    const navigate = useNavigate();
    const { user } = useAuth();
    const [month, setMonth] = useState(() => format(new Date(), 'yyyy-MM'));
    const [shiftData, setShiftData] = useState({});
    const [taskData, setTaskData] = useState({});
    const [loading, setLoading] = useState(false);
    const [loadError, setLoadError] = useState('');
    const [vacationBalance, setVacationBalance] = useState(null);
    const [selectedDate, setSelectedDate] = useState(null);
    const [focusShiftId, setFocusShiftId] = useState(null);
    const [focusTaskId, setFocusTaskId] = useState(null);

    const load = useCallback(async () => {
        setLoading(true);
        setLoadError('');
        try {
            const [shiftsRes, tasksRes] = await Promise.all([
                api.get('/shifts/calendar/', { params: { mesic: month, scope: 'mine' } }),
                taskAPI.getCalendar(month),
            ]);
            setShiftData(shiftsRes.data?.kalendar_data || {});
            setTaskData(tasksRes.kalendar_data || tasksRes?.data?.kalendar_data || {});
        } catch (err) {
            setShiftData({});
            setTaskData({});
            setLoadError(err?.response?.data?.error || err?.message || 'Nepodařilo se načíst kalendář.');
        } finally {
            setLoading(false);
        }
    }, [month]);

    useEffect(() => {
        load();
    }, [load]);

    useEffect(() => {
        const rok = month.split('-')[0];
        (async () => {
            try {
                const res = await api.get('/shifts/vacation-balance/', { params: { rok } });
                setVacationBalance(res.data);
            } catch {
                setVacationBalance(null);
            }
        })();
    }, [month]);

    const openDay = (dateStr, { shiftId, taskId } = {}) => {
        setSelectedDate(dateStr);
        setFocusShiftId(shiftId ?? null);
        setFocusTaskId(taskId ?? null);
    };

    const closeDay = () => {
        setSelectedDate(null);
        setFocusShiftId(null);
        setFocusTaskId(null);
    };

    const renderCell = (_date, { isCurrentMonth }) => {
        if (!isCurrentMonth) return null;
        const dateStr = format(_date, 'yyyy-MM-dd');
        const shifts = shiftData[dateStr] || [];
        const tasks = taskData[dateStr] || [];
        const workShifts = shifts.filter((s) => s.typ_smeny === 'prace');
        const absenceShifts = shifts.filter((s) => s.typ_smeny === 'dovolena' || s.typ_smeny === 'nemoc');
        const userStore = user?.prodejna_id
            ? { id: user.prodejna_id, nazev: user.prodejna, nazev_kratkiy: user.prodejna }
            : null;
        const closureNotice = getClosureNotice(dateStr, { userStore });
        return (
            <>
                {closureNotice && (
                    <div
                        className={`closure-notice closure-notice--${closureNotice.kind}`}
                        title={closureNotice.title}
                    >
                        {closureNotice.kind === 'always_closed' ? '🔒' : '⛪'} {closureNotice.label}
                    </div>
                )}
                {workShifts.length > 0 && (
                    <div className="shifts-container">
                        {workShifts.slice(0, 2).map((s) => (
                            <div
                                key={`s-${s.id}`}
                                className="shift-item mine profile-calendar-chip"
                                title={`${s.prodejna_nazev}: ${s.cas_od}–${s.cas_do}`}
                                onMouseDown={(e) => e.stopPropagation()}
                                onClick={(e) => {
                                    e.stopPropagation();
                                    openDay(dateStr, { shiftId: s.id });
                                }}
                            >
                                <div className="shift-content">
                                    <div className="shift-time">
                                        {formatShiftTime(s.cas_od)}–{formatShiftTime(s.cas_do)}
                                    </div>
                                    {s.prodejna_nazev && (
                                        <div className="shift-store">{s.prodejna_nazev}</div>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                )}
                {absenceShifts.length > 0 && (
                    <div className="shifts-absences">
                        {absenceShifts.slice(0, 2).map((s) => (
                            <div
                                key={`a-${s.id}`}
                                className={`shift-item shift-item--absence ${s.typ_smeny === 'dovolena' ? 'vacation' : 'sick'}`}
                                title={s.typ_smeny === 'dovolena' ? 'Dovolená' : 'Nemoc'}
                                onMouseDown={(e) => e.stopPropagation()}
                                onClick={(e) => {
                                    e.stopPropagation();
                                    openDay(dateStr, { shiftId: s.id });
                                }}
                            >
                                <span className="shift-absence-icon">{s.typ_smeny === 'dovolena' ? '🏖️' : '🏥'}</span>
                                <span className="shift-absence-name">{s.typ_smeny === 'dovolena' ? 'Dovolená' : 'Nemoc'}</span>
                            </div>
                        ))}
                    </div>
                )}
                {tasks.slice(0, 2).map((t) => (
                    <div
                        key={`t-${t.id}`}
                        className={`uc-task-chip profile-calendar-chip ${urgencyClassName(urgencyForTask(t))}`}
                        title={t.ukol}
                        onMouseDown={(e) => e.stopPropagation()}
                        onClick={(e) => {
                            e.stopPropagation();
                            openTask(navigate, t.id);
                        }}
                    >
                        {t.ukol?.slice(0, 12)}
                    </div>
                ))}
            </>
        );
    };

    return (
        <div className="profile-calendar">
            {loadError && (
                <p className="celkova-cisla-error">
                    {loadError}{' '}
                    <button type="button" className="btn-link" onClick={load}>Zkusit znovu</button>
                </p>
            )}
            {vacationBalance?.eligible && (
                <div className="profile-vacation-banner">
                    🏖️ Dovolená {vacationBalance.rok}: zbývá{' '}
                    <strong>{vacationBalance.zbyva_h} h</strong>
                    {' '}(čerpáno {vacationBalance.cerpano_h} / {vacationBalance.fond_h} h
                    {vacationBalance.odeceno_deficit_h > 0
                        ? `, vč. ${vacationBalance.odeceno_deficit_h} h deficit fondu`
                        : ''})
                </div>
            )}
            <div className="profile-calendar-legend">
                <span><span className="legend-dot legend-dot--shift" /> Směna</span>
                <span><span className="legend-dot legend-dot--task" /> Úkol</span>
                <span className="profile-calendar-hint muted">Klik na den = detail · klik na položku = rychlý náhled</span>
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
            <UnifiedCalendar
                month={month}
                variant="full"
                renderCellContent={renderCell}
                onDateClick={(dateStr) => openDay(dateStr)}
            />
            {selectedDate && (
                <ProfileDayPanel
                    dateStr={selectedDate}
                    shifts={shiftData[selectedDate] || []}
                    tasks={taskData[selectedDate] || []}
                    focusShiftId={focusShiftId}
                    focusTaskId={focusTaskId}
                    onClose={closeDay}
                    onRefresh={load}
                />
            )}
        </div>
    );
};

export default ProfileCalendar;
