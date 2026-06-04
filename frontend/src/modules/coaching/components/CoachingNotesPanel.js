import React, { useState } from 'react';
import { coachingAPI } from '../../../services/api';

const NOTE_TYPES = [
    { value: 'poznamka', label: 'Poznámka' },
    { value: 'jedna_na_jednoho', label: '1:1' },
    { value: 'zpetna_vazba', label: 'Zpětná vazba' },
];

const GOAL_STATES = [
    { value: 'otevreny', label: 'Otevřený' },
    { value: 'splneny', label: 'Splněný' },
    { value: 'zruseny', label: 'Zrušený' },
];

const fmtDate = (iso) => {
    if (!iso) return '';
    return new Date(iso).toLocaleString('cs-CZ', { dateStyle: 'short', timeStyle: 'short' });
};

const CoachingNotesPanel = ({ prodejceId, notes = [], goals = [], onRefresh }) => {
    const [noteForm, setNoteForm] = useState({ typ: 'poznamka', text: '' });
    const [goalForm, setGoalForm] = useState({ nazev: '', popis: '', termin: '' });
    const [saving, setSaving] = useState(false);

    const saveNote = async () => {
        if (!noteForm.text.trim()) return;
        setSaving(true);
        try {
            await coachingAPI.createNote({ prodejce_id: prodejceId, ...noteForm });
            setNoteForm({ typ: 'poznamka', text: '' });
            onRefresh?.();
        } finally {
            setSaving(false);
        }
    };

    const saveGoal = async () => {
        if (!goalForm.nazev.trim()) return;
        setSaving(true);
        try {
            await coachingAPI.createGoal({
                prodejce_id: prodejceId,
                nazev: goalForm.nazev,
                popis: goalForm.popis,
                termin: goalForm.termin || null,
                stav: 'otevreny',
            });
            setGoalForm({ nazev: '', popis: '', termin: '' });
            onRefresh?.();
        } finally {
            setSaving(false);
        }
    };

    const toggleGoal = async (goal) => {
        const next = goal.stav === 'otevreny' ? 'splneny' : 'otevreny';
        await coachingAPI.updateGoal(goal.id, { stav: next });
        onRefresh?.();
    };

    return (
        <div className="coaching-notes-panel">
            <div className="coaching-notes-col">
                <h4>Poznámky</h4>
                <div className="coaching-timeline">
                    {notes.map((n) => (
                        <article key={n.id} className="coaching-timeline-item">
                            <header>
                                <strong>{NOTE_TYPES.find((t) => t.value === n.typ)?.label || n.typ}</strong>
                                <span>{fmtDate(n.vytvoreno)} · {n.autor_jmeno}</span>
                            </header>
                            <p>{n.text}</p>
                        </article>
                    ))}
                    {!notes.length && <p className="coaching-muted">Zatím žádné poznámky</p>}
                </div>
                <div className="coaching-form">
                    <select value={noteForm.typ} onChange={(e) => setNoteForm((f) => ({ ...f, typ: e.target.value }))}>
                        {NOTE_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
                    </select>
                    <textarea
                        rows={3}
                        placeholder="Nová poznámka…"
                        value={noteForm.text}
                        onChange={(e) => setNoteForm((f) => ({ ...f, text: e.target.value }))}
                    />
                    <button type="button" disabled={saving} onClick={saveNote}>Uložit poznámku</button>
                </div>
            </div>
            <div className="coaching-notes-col">
                <h4>Cíle školení</h4>
                <ul className="coaching-goals-list">
                    {goals.map((g) => (
                        <li key={g.id} className={`coaching-goal coaching-goal--${g.stav}`}>
                            <div>
                                <strong>{g.nazev}</strong>
                                {g.termin && <span className="coaching-goal-term">do {g.termin}</span>}
                                {g.popis && <p>{g.popis}</p>}
                            </div>
                            <button type="button" onClick={() => toggleGoal(g)}>
                                {g.stav === 'otevreny' ? 'Splněno' : 'Znovu otevřít'}
                            </button>
                        </li>
                    ))}
                    {!goals.length && <p className="coaching-muted">Žádné aktivní cíle</p>}
                </ul>
                <div className="coaching-form">
                    <input
                        placeholder="Název cíle"
                        value={goalForm.nazev}
                        onChange={(e) => setGoalForm((f) => ({ ...f, nazev: e.target.value }))}
                    />
                    <input
                        type="date"
                        value={goalForm.termin}
                        onChange={(e) => setGoalForm((f) => ({ ...f, termin: e.target.value }))}
                    />
                    <textarea
                        rows={2}
                        placeholder="Popis (volitelně)"
                        value={goalForm.popis}
                        onChange={(e) => setGoalForm((f) => ({ ...f, popis: e.target.value }))}
                    />
                    <button type="button" disabled={saving} onClick={saveGoal}>Přidat cíl</button>
                </div>
            </div>
        </div>
    );
};

export default CoachingNotesPanel;
