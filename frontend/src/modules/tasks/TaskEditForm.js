import React, { useEffect, useState } from 'react';
import { taskAPI } from '../../services/api';
import { AnalyticsDateInput } from '../../components/AnalyticsDateRange';
import { TaskAssigneeOptions } from './TaskAssigneeOptions';

function deadlineToInput(deadline) {
    if (!deadline) return '';
    const d = String(deadline).slice(0, 10);
    return d;
}

function timeToInput(deadlineCas) {
    if (!deadlineCas) return '';
    return String(deadlineCas).slice(0, 5);
}

const TaskEditForm = ({
    task,
    storeOptions,
    storeLocked = false,
    onSaved,
    onCancel,
}) => {
    const [form, setForm] = useState({
        ukol: task.ukol || '',
        priorita: task.priorita || 'stredni',
        deadline: deadlineToInput(task.deadline),
        deadline_cas: timeToInput(task.deadline_cas),
        id_prodejny: task.id_prodejny ? String(task.id_prodejny) : '',
        id_prodejce_ukol: task.id_prodejce_ukol ? String(task.id_prodejce_ukol) : '',
        stav: task.stav || 'novy',
    });
    const [assignees, setAssignees] = useState([]);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState('');

    useEffect(() => {
        setForm({
            ukol: task.ukol || '',
            priorita: task.priorita || 'stredni',
            deadline: deadlineToInput(task.deadline),
            deadline_cas: timeToInput(task.deadline_cas),
            id_prodejny: task.id_prodejny ? String(task.id_prodejny) : '',
            id_prodejce_ukol: task.id_prodejce_ukol ? String(task.id_prodejce_ukol) : '',
            stav: task.stav || 'novy',
        });
    }, [task]);

    useEffect(() => {
        const storeId = form.id_prodejny;
        if (!storeId) {
            setAssignees([]);
            return;
        }
        let cancelled = false;
        taskAPI.getAssignees(storeId).then((res) => {
            if (!cancelled) setAssignees(res.assignees || []);
        }).catch(() => {
            if (!cancelled) setAssignees([]);
        });
        return () => { cancelled = true; };
    }, [form.id_prodejny]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!form.ukol.trim()) {
            setError('Text úkolu je povinný.');
            return;
        }
        if (task.typ === 'prirazeny' && (!form.id_prodejny || !form.id_prodejce_ukol)) {
            setError('U přiřazeného úkolu vyberte pobočku a zaměstnance.');
            return;
        }
        setSaving(true);
        setError('');
        try {
            const payload = {
                ukol: form.ukol.trim(),
                priorita: form.priorita,
                stav: form.stav,
                deadline: form.deadline || null,
                deadline_cas: form.deadline_cas || null,
            };
            if (task.typ === 'prirazeny') {
                payload.id_prodejny = Number(form.id_prodejny);
                payload.id_prodejce_ukol = Number(form.id_prodejce_ukol);
            }
            const updated = await taskAPI.update(task.id, payload);
            onSaved?.(updated);
        } catch (err) {
            setError(err?.response?.data?.error || err?.message || 'Uložení se nezdařilo.');
        } finally {
            setSaving(false);
        }
    };

    const isPrirazeny = task.typ === 'prirazeny';

    return (
        <form className="task-edit-form" onSubmit={handleSubmit}>
            <h4 className="task-edit-title">Upravit úkol</h4>
            <textarea
                className="task-control task-control--text task-edit-text"
                rows={3}
                value={form.ukol}
                onChange={(e) => setForm({ ...form, ukol: e.target.value })}
            />
            {isPrirazeny && (
                <div className="task-form-row task-form-row--meta">
                    <select
                        className="task-select"
                        value={form.id_prodejny}
                        disabled={storeLocked}
                        onChange={(e) => setForm({
                            ...form,
                            id_prodejny: e.target.value,
                            id_prodejce_ukol: '',
                        })}
                    >
                        <option value="">Pobočka…</option>
                        {storeOptions.map((s) => (
                            <option key={s.id} value={s.id}>
                                {s.nazev_kratkiy || s.nazev}
                            </option>
                        ))}
                    </select>
                    <select
                        className="task-select"
                        value={form.id_prodejce_ukol}
                        disabled={!form.id_prodejny}
                        onChange={(e) => setForm({ ...form, id_prodejce_ukol: e.target.value })}
                    >
                        <TaskAssigneeOptions assignees={assignees} placeholder="Přiřadit…" />
                    </select>
                </div>
            )}
            <div className="task-form-row task-form-row--meta">
                <select
                    className="task-select task-select--prio"
                    value={form.priorita}
                    onChange={(e) => setForm({ ...form, priorita: e.target.value })}
                >
                    <option value="nizka">Nízká</option>
                    <option value="stredni">Střední</option>
                    <option value="vysoka">Vysoká</option>
                </select>
                <select
                    className="task-select"
                    value={form.stav}
                    onChange={(e) => setForm({ ...form, stav: e.target.value })}
                >
                    <option value="novy">Nový</option>
                    <option value="v_procesu">V procesu</option>
                    <option value="hotovo">Hotovo</option>
                </select>
            </div>
            <div className="task-form-row task-form-row--deadline">
                <div className="task-date-field">
                    <AnalyticsDateInput
                        value={form.deadline}
                        onApply={(deadline) => setForm((f) => ({ ...f, deadline }))}
                        showError={false}
                        inputClassName="task-control task-control--date"
                    />
                </div>
                <input
                    type="time"
                    className="task-control task-control--time"
                    value={form.deadline_cas}
                    onChange={(e) => setForm({ ...form, deadline_cas: e.target.value })}
                />
            </div>
            {error && <p className="task-edit-error">{error}</p>}
            <div className="task-edit-actions">
                <button type="submit" className="btn-primary" disabled={saving}>
                    {saving ? 'Ukládám…' : 'Uložit změny'}
                </button>
                <button type="button" className="btn-outline" onClick={onCancel} disabled={saving}>
                    Zrušit
                </button>
            </div>
        </form>
    );
};

export default TaskEditForm;
