import React, { useState, useEffect } from 'react';
import './WreckPartForm.css';

const WreckPartForm = ({ initial, onSave, onCancel }) => {
    const [form, setForm] = useState({
        model_name: '',
        part_type: 'LCD',
        quantity: 1,
        store: '',
        notes: '',
    });
    const [saving, setSaving] = useState(false);

    useEffect(() => {
        if (initial) {
            setForm({
                model_name: initial.model_name || '',
                part_type: initial.part_type || 'LCD',
                quantity: initial.quantity || 1,
                store: initial.store || '',
                notes: initial.notes || '',
            });
        }
    }, [initial]);

    const handleChange = (e) => {
        const { name, value } = e.target;
        setForm((prev) => ({
            ...prev,
            [name]: name === 'quantity' ? parseInt(value, 10) || 1 : value,
        }));
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setSaving(true);
        try {
            await onSave(form);
        } finally {
            setSaving(false);
        }
    };

    return (
        <div className="wreck-part-form-overlay">
            <form className="wreck-part-form" onSubmit={handleSubmit}>
                <h3>{initial ? 'Upravit díl' : 'Nový díl z vraku'}</h3>
                <label>
                    Model
                    <input name="model_name" value={form.model_name} onChange={handleChange} required />
                </label>
                <label>
                    Typ dílu
                    <input name="part_type" value={form.part_type} onChange={handleChange} required />
                </label>
                <label>
                    Počet
                    <input name="quantity" type="number" min="1" value={form.quantity} onChange={handleChange} />
                </label>
                <label>
                    Prodejna
                    <input name="store" value={form.store} onChange={handleChange} required />
                </label>
                <label>
                    Poznámka
                    <textarea name="notes" value={form.notes} onChange={handleChange} rows={3} />
                </label>
                <div className="wreck-part-form__actions">
                    <button type="button" className="btn btn-outline" onClick={onCancel}>Zrušit</button>
                    <button type="submit" className="btn btn-primary" disabled={saving}>
                        {saving ? 'Ukládám…' : 'Uložit'}
                    </button>
                </div>
            </form>
        </div>
    );
};

export default WreckPartForm;
