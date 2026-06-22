import React, { useEffect, useState } from 'react';
import { format } from 'date-fns';
import { cs } from 'date-fns/locale';
import { useAuth } from '../../context/AuthContext';
import { taskAPI } from '../../services/api';
import TaskUrgencyBadge from './TaskUrgencyBadge';
import TaskComments from './TaskComments';
import TaskStatusIcon from '../../components/TaskStatusIcon';
import {
    taskDisplayTitle,
    isPrirazenySop,
    STAV_LABELS,
} from '../../utils/taskDisplay';

const TaskDetailPanel = ({
    task,
    onUpdate,
    onClose,
    canEdit = true,
    showMarkRead = true,
    isManager = false,
    layout = 'inline',
}) => {
    const { user, isAdmin, canManageTasks } = useAuth();
    const [startOpen, setStartOpen] = useState(false);
    const [prvniKrok, setPrvniKrok] = useState('');
    const [blockOpen, setBlockOpen] = useState(false);
    const [blockReason, setBlockReason] = useState('');
    const [dodLocal, setDodLocal] = useState([]);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState('');

    useEffect(() => {
        if (!task || !showMarkRead) return;
        if (task.typ === 'prirazeny' && !task.precteno_v) {
            taskAPI.markRead(task.id).then((updated) => {
                onUpdate?.({ ...task, precteno_v: updated.precteno_v });
            }).catch(() => {});
        }
    }, [task?.id]); // eslint-disable-line react-hooks/exhaustive-deps

    useEffect(() => {
        setDodLocal(task?.dod_polozky || []);
        setPrvniKrok(task?.prvni_krok || '');
        setBlockReason(task?.blokovano_duvod || '');
        setError('');
    }, [task?.id, task?.dod_polozky, task?.prvni_krok, task?.blokovano_duvod]);

    if (!task) {
        return (
            <div className="task-detail-panel task-detail-panel--empty">
                <p className="muted">Vyberte úkol ze seznamu</p>
            </div>
        );
    }

    const sop = isPrirazenySop(task);
    const title = taskDisplayTitle(task);
    const isAssignee = task.id_prodejce_ukol === user?.id
        || (task.typ === 'osobni' && task.id_prodejce_zadal === user?.id);
    const canManageDod = isManager && canManageTasks() && (isAdmin() || Boolean(task.id_prodejny));
    const canToggleDod = canEdit && task.stav !== 'hotovo' && (isAssignee || canManageDod);
    const canAssigneeActions = canEdit && isAssignee;
    const canActOnTask = canEdit && (isManager || isAssignee);

    const saveUpdate = async (payload) => {
        setSaving(true);
        setError('');
        try {
            const updated = await taskAPI.update(task.id, payload);
            onUpdate?.(updated);
            return updated;
        } catch (err) {
            setError(err?.response?.data?.error || 'Uložení se nezdařilo.');
            return null;
        } finally {
            setSaving(false);
        }
    };

    const handleStart = async (e) => {
        e.preventDefault();
        if (!prvniKrok.trim()) {
            setError('První krok je povinný.');
            return;
        }
        const updated = await saveUpdate({
            stav: 'v_procesu',
            prvni_krok: prvniKrok.trim(),
        });
        if (updated) setStartOpen(false);
    };

    const handleBlock = async (e) => {
        e.preventDefault();
        if (!blockReason.trim()) {
            setError('Důvod blokace je povinný.');
            return;
        }
        const updated = await saveUpdate({
            stav: 'blokovany',
            blokovano_duvod: blockReason.trim(),
        });
        if (updated) setBlockOpen(false);
    };

    const toggleDod = async (index) => {
        if (!canToggleDod) return;
        const next = dodLocal.map((p, i) => (
            i === index ? { ...p, splneno: !p.splneno } : p
        ));
        setDodLocal(next);
        await saveUpdate({ dod_polozky: next });
    };

    const handleComplete = async () => {
        const payload = { stav: 'hotovo', dod_polozky: dodLocal };
        await saveUpdate(payload);
    };

    const handleApprove = async () => {
        await saveUpdate({ stav: 'hotovo' });
    };

    const handleReturnToProcess = async () => {
        await saveUpdate({ stav: 'v_procesu' });
    };

    const handleMidCheckpoint = async () => {
        await saveUpdate({ potvrdit_mid_kontrolu: true });
    };

    const handleUnblock = async () => {
        await saveUpdate({ stav: 'v_procesu', blokovano_duvod: '' });
    };

    const deadlineStr = task.deadline
        ? format(new Date(task.deadline), 'd. M. yyyy', { locale: cs })
        : null;
    const timeStr = task.deadline_cas ? String(task.deadline_cas).slice(0, 5) : null;
    const allDodDone = dodLocal.length > 0 && dodLocal.every((p) => p.splneno);
    const canComplete = sop && canAssigneeActions
        && ['v_procesu', 'blokovany'].includes(task.stav) && allDodDone;

    const panelClass = [
        'task-detail-panel',
        layout === 'page' ? 'task-detail-panel--page' : '',
    ].filter(Boolean).join(' ');

    const actionButtons = canActOnTask && task.stav !== 'hotovo' ? (
        <>
            {sop && task.stav === 'novy' && canAssigneeActions && (
                <button
                    type="button"
                    className="btn btn--primary"
                    disabled={saving}
                    onClick={() => setStartOpen(true)}
                >
                    Začít řešit
                </button>
            )}
            {sop && canAssigneeActions && ['v_procesu', 'blokovany'].includes(task.stav) && (
                <>
                    {task.stav === 'v_procesu' && !task.mid_kontrola_v && (
                        <button
                            type="button"
                            className="btn btn--ghost"
                            disabled={saving}
                            onClick={handleMidCheckpoint}
                        >
                            Kontrola průběhu
                        </button>
                    )}
                    {task.stav === 'v_procesu' && (
                        <button
                            type="button"
                            className="btn btn--ghost"
                            disabled={saving}
                            onClick={() => setBlockOpen(true)}
                        >
                            Blokováno
                        </button>
                    )}
                    {task.stav === 'blokovany' && (
                        <button
                            type="button"
                            className="btn btn--ghost"
                            disabled={saving}
                            onClick={handleUnblock}
                        >
                            Odblokovat
                        </button>
                    )}
                </>
            )}
            {canComplete && (
                <button
                    type="button"
                    className="btn btn--primary"
                    disabled={saving}
                    onClick={handleComplete}
                >
                    {task.vyzaduje_schvaleni ? 'Odeslat ke schválení' : 'Označit hotovo'}
                </button>
            )}
            {isManager && task.stav === 'ceka_schvaleni' && (
                <>
                    <button
                        type="button"
                        className="btn btn--primary"
                        disabled={saving}
                        onClick={handleApprove}
                    >
                        Schválit a uzavřít
                    </button>
                    <button
                        type="button"
                        className="btn btn--ghost"
                        disabled={saving}
                        onClick={handleReturnToProcess}
                    >
                        Vrátit do procesu
                    </button>
                </>
            )}
            {!sop && task.stav === 'novy' && (
                <button
                    type="button"
                    className="btn btn--ghost"
                    disabled={saving}
                    onClick={() => saveUpdate({ stav: 'v_procesu' })}
                >
                    Začít řešit
                </button>
            )}
            {!sop && task.stav !== 'hotovo' && (
                <button
                    type="button"
                    className="btn btn--primary"
                    disabled={saving}
                    onClick={() => saveUpdate({ stav: 'hotovo' })}
                >
                    Označit hotovo
                </button>
            )}
        </>
    ) : null;

    return (
        <div className={panelClass}>
            <div className="task-detail-panel__scroll">
                <div className="task-detail-header">
                    <TaskStatusIcon task={task} size="lg" className="task-detail-icon" />
                    <h3>{title}</h3>
                    {onClose && (
                        <button type="button" className="btn-icon" onClick={onClose} aria-label="Zavřít detail">
                            <i className="fas fa-times" />
                        </button>
                    )}
                </div>

                {sop && task.vysledek && task.vysledek !== title && (
                    <div className="task-detail-section">
                        <strong>Výsledek</strong>
                        <p className="task-detail-text">{task.vysledek}</p>
                    </div>
                )}

                {sop && task.popis && (
                    <div className="task-detail-section">
                        <strong>Popis</strong>
                        <p className="task-detail-text">{task.popis}</p>
                    </div>
                )}

                {sop && dodLocal.length > 0 && (
                    <div className="task-detail-section">
                        <strong>Definition of Done</strong>
                        <ul className="task-dod-checklist">
                            {dodLocal.map((p, i) => (
                                <li
                                    key={`${p.text}-${i}`}
                                    className={`task-dod-checklist__item${p.splneno ? ' is-done' : ''}`}
                                >
                                    <button
                                        type="button"
                                        className="task-dod-checklist__check"
                                        disabled={!canToggleDod}
                                        onClick={() => toggleDod(i)}
                                        aria-pressed={!!p.splneno}
                                        aria-label={p.splneno ? 'Splněno' : 'Označit jako splněné'}
                                    >
                                        {p.splneno && <i className="fas fa-check" aria-hidden />}
                                    </button>
                                    <span className="task-dod-checklist__text">{p.text}</span>
                                </li>
                            ))}
                        </ul>
                    </div>
                )}

                <div className="task-detail-badges">
                    <span className={`task-status-badge task-status-badge--${task.stav}`}>
                        {STAV_LABELS[task.stav] || task.stav}
                    </span>
                    <TaskUrgencyBadge task={task} />
                </div>

                <div className="task-detail-meta">
                    <span><strong>Priorita</strong> {task.priorita}</span>
                    {deadlineStr && (
                        <span>
                            <strong>Termín</strong>
                            {deadlineStr}
                            {timeStr ? ` ${timeStr}` : ''}
                        </span>
                    )}
                    {task.typ === 'prirazeny' && task.zadavatel && (
                        <span><strong>Od</strong> {task.zadavatel.jmeno_plne || task.zadavatel.jmeno}</span>
                    )}
                    {task.typ === 'prirazeny' && !task.prodejna && (
                        <span><strong>Pobočka</strong> Bez pobočky</span>
                    )}
                    {task.prodejna && (
                        <span><strong>Pobočka</strong> {task.prodejna.nazev}</span>
                    )}
                    {task.assignee && task.typ === 'prirazeny' && (
                        <span><strong>Přiřazeno</strong> {task.assignee.jmeno_plne}</span>
                    )}
                    {task.stav === 'blokovany' && task.blokovano_duvod && (
                        <span><strong>Blokace</strong> {task.blokovano_duvod}</span>
                    )}
                    {task.vyzaduje_schvaleni && (
                        <span><strong>Schválení</strong> Vyžaduje vedoucího</span>
                    )}
                </div>

                {sop && (task.start_potvrzeno_v || task.mid_kontrola_v || task.schvaleno_v) && (
                    <div className="task-detail-section task-detail-timeline">
                        <strong>Průběh</strong>
                        <ul className="task-timeline">
                            <li>Vytvořeno: {format(new Date(task.vytvoreno), 'd. M. yyyy HH:mm', { locale: cs })}</li>
                            {task.start_potvrzeno_v && (
                                <li>
                                    Start: {format(new Date(task.start_potvrzeno_v), 'd. M. yyyy HH:mm', { locale: cs })}
                                    {task.prvni_krok ? ` – ${task.prvni_krok}` : ''}
                                </li>
                            )}
                            {task.mid_kontrola_v && (
                                <li>
                                    Kontrola průběhu: {format(new Date(task.mid_kontrola_v), 'd. M. yyyy HH:mm', { locale: cs })}
                                </li>
                            )}
                            {task.schvaleno_v && (
                                <li>
                                    Schváleno: {format(new Date(task.schvaleno_v), 'd. M. yyyy HH:mm', { locale: cs })}
                                    {task.schvalil?.jmeno_plne ? ` (${task.schvalil.jmeno_plne})` : ''}
                                </li>
                            )}
                        </ul>
                    </div>
                )}

                {error && <p className="task-edit-error">{error}</p>}

                <TaskComments
                    taskId={task.id}
                    onCommentAdded={() => onUpdate?.({
                        ...task,
                        komentare_count: (task.komentare_count || 0) + 1,
                    })}
                />
            </div>

            {actionButtons && (
                <div className="task-detail-panel__footer">
                    <div className="task-detail-actions">
                        {actionButtons}
                    </div>
                </div>
            )}

            {startOpen && (
                <div className="task-modal-overlay" role="dialog" aria-modal="true">
                    <form className="task-modal" onSubmit={handleStart}>
                        <div className="task-modal__header">
                            <h4>Start checkpoint</h4>
                            <p>Rozumíš výsledku úkolu?</p>
                        </div>
                        <div className="task-modal__body">
                            <p className="task-modal-outcome">{task.vysledek || title}</p>
                            <label className="task-modal-label">
                                První krok *
                                <input
                                    className="task-control task-control--text"
                                    value={prvniKrok}
                                    onChange={(e) => setPrvniKrok(e.target.value)}
                                    placeholder="Co uděláš jako první?"
                                    autoFocus
                                />
                            </label>
                            <div className="task-modal-actions">
                                <button type="submit" className="btn btn--primary" disabled={saving}>
                                    Zahájit úkol
                                </button>
                                <button type="button" className="btn btn--ghost" onClick={() => setStartOpen(false)}>
                                    Zrušit
                                </button>
                            </div>
                        </div>
                    </form>
                </div>
            )}

            {blockOpen && (
                <div className="task-modal-overlay" role="dialog" aria-modal="true">
                    <form className="task-modal" onSubmit={handleBlock}>
                        <div className="task-modal__header">
                            <h4>Blokovaný úkol</h4>
                            <p>Co brání dokončení?</p>
                        </div>
                        <div className="task-modal__body">
                            <label className="task-modal-label">
                                Důvod *
                                <textarea
                                    className="task-control task-control--text"
                                    rows={3}
                                    value={blockReason}
                                    onChange={(e) => setBlockReason(e.target.value)}
                                    placeholder="Popiš překážku…"
                                    autoFocus
                                />
                            </label>
                            <div className="task-modal-actions">
                                <button type="submit" className="btn btn--primary" disabled={saving}>
                                    Označit jako blokovaný
                                </button>
                                <button type="button" className="btn btn--ghost" onClick={() => setBlockOpen(false)}>
                                    Zrušit
                                </button>
                            </div>
                        </div>
                    </form>
                </div>
            )}
        </div>
    );
};

export default TaskDetailPanel;
