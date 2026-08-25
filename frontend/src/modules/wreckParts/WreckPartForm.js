import React, { useState, useEffect } from 'react';
import Modal from '../../components/Modal';
import './WreckPartForm.css';

const WreckPartForm = ({ initial, defaultStore = '', onSave, onCancel }) => {
    const [form, setForm] = useState({
        model_name: '',
        part_type: 'LCD',
        quantity: 1,
        store: defaultStore || 'Globus',
        notes: '',
    });
    const [saving, setSaving] = useState(false);

    useEffect(() => {
        if (initial) {
            setForm({
                model_name: initial.model_name || '',
                part_type: initial.part_type || 'LCD',
                quantity: initial.quantity || 1,
                store: initial.store || 'Globus',
                notes: initial.notes || '',
            });
        } else {
            setForm({
                model_name: '',
                part_type: 'LCD',
                quantity: 1,
                store: defaultStore || 'Globus',
                notes: '',
            });
        }
    }, [initial, defaultStore]);

    const handleChange = (e) => {
        const { name, value } = e.target;
        setForm((prev) => ({
            ...prev,
            [name]: name === 'quantity' ? parseInt(value, 10) || 1 : value,
        }));
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (saving) return;
        setSaving(true);
        try {
            await onSave(form);
        } finally {
            setSaving(false);
        }
    };

    return (
        <Modal
            title={initial ? 'Upravit díl' : 'Nový díl z vraku'}
            onClose={onCancel}
            size="sm"
            onSubmit={handleSubmit}
            bodyClassName="wreck-part-form"
            footer={(
                <>
                    <button type="button" className="btn-cancel" onClick={onCancel}>
                        Zrušit
                    </button>
                    <button type="submit" className="btn-submit" disabled={saving}>
                        {saving ? 'Ukládám…' : 'Uložit'}
                    </button>
                </>
            )}
        >
            <div className="form-group">
                <label htmlFor="wp_model_name">Model *</label>
                <input
                    id="wp_model_name"
                    name="model_name"
                    value={form.model_name}
                    onChange={handleChange}
                    required
                    autoComplete="off"
                    placeholder="iPhone 8"
                />
            </div>

            <div className="form-row">
                <div className="form-group">
                    <label htmlFor="wp_part_type">Typ dílu *</label>
                    <input
                        id="wp_part_type"
                        name="part_type"
                        value={form.part_type}
                        onChange={handleChange}
                        required
                        autoComplete="off"
                        placeholder="LCD"
                    />
                </div>
                <div className="form-group">
                    <label htmlFor="wp_quantity">Počet</label>
                    <input
                        id="wp_quantity"
                        name="quantity"
                        type="number"
                        min="1"
                        value={form.quantity}
                        onChange={handleChange}
                    />
                </div>
            </div>

            <div className="form-group">
                <label htmlFor="wp_store">Prodejna *</label>
                <input
                    id="wp_store"
                    name="store"
                    value={form.store}
                    onChange={handleChange}
                    required
                    autoComplete="off"
                    placeholder="Globus"
                />
            </div>

            <div className="form-group">
                <label htmlFor="wp_notes">Poznámka</label>
                <textarea
                    id="wp_notes"
                    name="notes"
                    value={form.notes}
                    onChange={handleChange}
                    rows={2}
                    placeholder="Volitelně…"
                />
            </div>
        </Modal>
    );
};

export default WreckPartForm;
