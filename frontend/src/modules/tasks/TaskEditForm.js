import React, { useEffect, useMemo, useState } from 'react';
import { taskAPI } from '../../services/api';
import { AnalyticsDateInput } from '../../components/AnalyticsDateRange';
import { Select } from '../../components/ui';
import { buildAssigneeSelectOptions } from './TaskAssigneeOptions';
import { taskDisplayTitle } from '../../utils/taskDisplay';

const PRIORITY_OPTIONS = [
    { value: 'nizka', label: 'Nízká' },
    { value: 'stredni', label: 'Střední' },
    { value: 'vysoka', label: 'Vysoká' },
];

const STATUS_OPTIONS = [
    { value: 'novy', label: 'Nový' },
    { value: 'v_procesu', label: 'V procesu' },
    { value: 'blokovany', label: 'Blokovaný' },
    { value: 'ceka_schvaleni', label: 'Čeká schválení' },
    { value: 'hotovo', label: 'Hotovo' },
];

function deadlineToInput(deadline) {
    if (!deadline) return '';
    return String(deadline).slice(0, 10);
}

function timeToInput(deadlineCas) {
    if (!deadlineCas) return '';
    return String(deadlineCas).slice(0, 5);
}

const TaskEditForm = ({
    task,
    storeOptions,
    storeLocked = false,
    isAdmin = false,
    onSaved,
    onCancel,
}) => {
    const initialBezPobocky = task.typ === 'prirazeny' && !task.id_prodejny;
    const [form, setForm] = useState({
        ukol: task.ukol || '',
        vysledek: task.vysledek || task.ukol || '',
        popis: task.popis || '',
        dod_polozky: task.dod_polozky || [],
        priorita: task.priorita || 'stredni',
        termin_zadani: deadlineToInput(task.termin_zadani),
        deadline: deadlineToInput(task.deadline),
        deadline_cas: timeToInput(task.deadline_cas),
        id_prodejny: task.id_prodejny ? String(task.id_prodejny) : '',
        id_prodejce_ukol: task.id_prodejce_ukol ? String(task.id_prodejce_ukol) : '',
        stav: task.stav || 'novy',
        vyzaduje_schvaleni: !!task.vyzaduje_schvaleni,
        bezPobocky: initialBezPobocky,
    });
    const [assignees, setAssignees] = useState([]);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState('');

    const storeSelectOptions = useMemo(
        () => [
            { value: '', label: 'Pobočka…' },
            ...storeOptions.map((s) => ({
                value: String(s.id),
                label: s.nazev_kratkiy || s.nazev,
            })),
        ],
        [storeOptions],
    );

    const assigneeSelectOptions = useMemo(
        () => buildAssigneeSelectOptions(assignees, 'Přiřadit…'),
        [assignees],
    );

    useEffect(() => {
        const bezPobocky = task.typ === 'prirazeny' && !task.id_prodejny;
        setForm({
            ukol: task.ukol || '',
            vysledek: task.vysledek || task.ukol || '',
            popis: task.popis || '',
            dod_polozky: task.dod_polozky || [],
            priorita: task.priorita || 'stredni',
            termin_zadani: deadlineToInput(task.termin_zadani),
            deadline: deadlineToInput(task.deadline),
            deadline_cas: timeToInput(task.deadline_cas),
            id_prodejny: task.id_prodejny ? String(task.id_prodejny) : '',
            id_prodejce_ukol: task.id_prodejce_ukol ? String(task.id_prodejce_ukol) : '',
            stav: task.stav || 'novy',
            vyzaduje_schvaleni: !!task.vyzaduje_schvaleni,
            bezPobocky,
        });
    }, [task]);

    useEffect(() => {
        if (task.typ !== 'prirazeny') return undefined;
        let cancelled = false;
        const load = async () => {
            try {
                const res = form.bezPobocky && isAdmin
                    ? await taskAPI.getAssignees(null, { storeless: true })
                    : await taskAPI.getAssignees(form.id_prodejny);
                if (!cancelled) setAssignees(res.assignees || []);
            } catch {
                if (!cancelled) setAssignees([]);
            }
        };
        if (form.bezPobocky && isAdmin) {
            load();
        } else if (form.id_prodejny) {
            load();
        } else {
            setAssignees([]);
        }
        return () => { cancelled = true; };
    }, [form.id_prodejny, form.bezPobocky, isAdmin, task.typ]);

    const updateDod = (index, text) => {
        setForm((f) => {
            const dod = [...f.dod_polozky];
            dod[index] = { ...dod[index], text };
            return { ...f, dod_polozky: dod };
        });
    };

    const addDodRow = () => {
        setForm((f) => ({
            ...f,
            dod_polozky: [...f.dod_polozky, { text: '', splneno: false }],
        }));
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (saving) return;
        const title = form.vysledek.trim() || form.ukol.trim();
        if (!title) {
            setError('Výsledek úkolu je povinný.');
            return;
        }
        if (task.typ === 'prirazeny' && !form.bezPobocky && (!form.id_prodejny || !form.id_prodejce_ukol)) {
            setError('U přiřazeného úkolu vyberte pobočku a zaměstnance.');
            return;
        }
        if (task.typ === 'prirazeny' && form.bezPobocky && !form.id_prodejce_ukol) {
            setError('Vyberte přiřazeného uživatele.');
            return;
        }
        if (task.typ === 'prirazeny' && !form.deadline) {
            setError('U přiřazeného úkolu je povinný termín dokončení.');
            return;
        }
        const dod = form.dod_polozky
            .map((p) => ({ text: (p.text || '').trim(), splneno: !!p.splneno }))
            .filter((p) => p.text);
        if (task.typ === 'prirazeny' && dod.length < 1) {
            setError('Přidejte alespoň jednu položku Definition of Done.');
            return;
        }
        setSaving(true);
        setError('');
        try {
            const payload = {
                ukol: title.split('\n')[0].slice(0, 255),
                vysledek: title,
                popis: form.popis.trim(),
                dod_polozky: task.typ === 'prirazeny' ? dod : undefined,
                priorita: form.priorita,
                stav: form.stav,
                termin_zadani: form.termin_zadani || null,
                deadline: form.deadline || null,
                deadline_cas: form.deadline_cas || null,
                vyzaduje_schvaleni: form.vyzaduje_schvaleni,
            };
            if (task.typ === 'prirazeny') {
                payload.id_prodejny = form.bezPobocky ? null : Number(form.id_prodejny);
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
            <h4 className="task-edit-title">Upravit úkol: {taskDisplayTitle(task)}</h4>
            {isPrirazeny ? (
                <>
                    <label className="task-form-label">
                        Výsledek *
                        <textarea
                            className="task-control task-control--text task-edit-text"
                            rows={3}
                            value={form.vysledek}
                            onChange={(e) => setForm({ ...form, vysledek: e.target.value })}
                        />
                    </label>
                    <label className="task-form-label">
                        Popis
                        <textarea
                            className="task-control task-control--text"
                            rows={2}
                            value={form.popis}
                            onChange={(e) => setForm({ ...form, popis: e.target.value })}
                        />
                    </label>
                    <div className="task-dod-editor">
                        <p className="task-dod-editor__title">Definition of Done *</p>
                        {form.dod_polozky.map((row, i) => (
                            <div key={i} className="task-dod-editor-row">
                                <span className="task-dod-editor-row__num">{i + 1}</span>
                                <input
                                    className="task-control task-control--text"
                                    value={row.text || ''}
                                    onChange={(e) => updateDod(i, e.target.value)}
                                />
                            </div>
                        ))}
                        <button type="button" className="btn btn--ghost task-dod-add-btn" onClick={addDodRow}>
                            + Přidat položku
                        </button>
                    </div>
                </>
            ) : (
                <textarea
                    className="task-control task-control--text task-edit-text"
                    rows={3}
                    value={form.ukol}
                    onChange={(e) => setForm({ ...form, ukol: e.target.value })}
                />
            )}
            {isPrirazeny && isAdmin && (
                <div className="task-toggle-row">
                    <label className="task-toggle" htmlFor={`bez-pobocky-edit-${task.id}`}>
                        <input
                            id={`bez-pobocky-edit-${task.id}`}
                            type="checkbox"
                            checked={form.bezPobocky}
                            onChange={(e) => setForm({
                                ...form,
                                bezPobocky: e.target.checked,
                                id_prodejny: e.target.checked ? '' : form.id_prodejny,
                                id_prodejce_ukol: '',
                            })}
                        />
                        <span className="task-toggle__track" />
                        <span className="task-toggle__thumb" />
                    </label>
                    <label className="task-toggle-label" htmlFor={`bez-pobocky-edit-${task.id}`}>
                        Bez pobočky
                    </label>
                </div>
            )}
            {isPrirazeny && (
                <div className={`task-form-row ${form.bezPobocky ? 'task-form-row--assign' : 'task-form-row--meta'}`}>
                    {!form.bezPobocky && (
                        <Select
                            className="task-select"
                            options={storeSelectOptions}
                            value={form.id_prodejny}
                            disabled={storeLocked}
                            onChange={(id_prodejny) => setForm({
                                ...form,
                                id_prodejny,
                                id_prodejce_ukol: '',
                            })}
                            placeholder="Pobočka…"
                        />
                    )}
                    <Select
                        className="task-select"
                        options={assigneeSelectOptions}
                        value={form.id_prodejce_ukol}
                        disabled={!form.bezPobocky && !form.id_prodejny}
                        onChange={(id_prodejce_ukol) => setForm({ ...form, id_prodejce_ukol })}
                        placeholder="Přiřadit…"
                    />
                </div>
            )}
            <div className="task-form-row task-form-row--meta">
                <Select
                    className="task-select task-select--prio"
                    options={PRIORITY_OPTIONS}
                    value={form.priorita}
                    onChange={(priorita) => setForm({ ...form, priorita })}
                    placeholder="Priorita"
                />
                <Select
                    className="task-select"
                    options={STATUS_OPTIONS}
                    value={form.stav}
                    onChange={(stav) => setForm({ ...form, stav })}
                    placeholder="Stav"
                />
            </div>
            {isPrirazeny && (
                <label className="task-checkbox-label">
                    <input
                        type="checkbox"
                        checked={form.vyzaduje_schvaleni}
                        onChange={(e) => setForm({
                            ...form,
                            vyzaduje_schvaleni: e.target.checked,
                        })}
                    />
                    Vyžaduje schválení
                </label>
            )}
            <div className="task-form-row task-form-row--deadlines">
                <label className="task-form-label">
                    Termín zadání
                    <div className="task-date-field">
                        <AnalyticsDateInput
                            value={form.termin_zadani}
                            onApply={(termin_zadani) => setForm((f) => ({ ...f, termin_zadani }))}
                            showError={false}
                            inputClassName="task-control task-control--date"
                        />
                    </div>
                </label>
                <label className="task-form-label">
                    Termín dokončení
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
                            aria-label="Čas dokončení"
                        />
                    </div>
                </label>
            </div>
            {error && <p className="task-edit-error">{error}</p>}
            <div className="task-edit-actions">
                <button type="submit" className="btn btn--primary" disabled={saving}>
                    {saving ? 'Ukládám…' : 'Uložit změny'}
                </button>
                <button type="button" className="btn btn--ghost" onClick={onCancel} disabled={saving}>
                    Zrušit
                </button>
            </div>
        </form>
    );
};

export default TaskEditForm;
