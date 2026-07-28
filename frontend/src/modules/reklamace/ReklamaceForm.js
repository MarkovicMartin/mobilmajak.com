import React, { useState } from 'react';
import Modal from '../../components/Modal';
import './ReklamaceForm.css';

const emptyForm = {
    jejich_oznaceni: '',
    nazev_zbozi: '',
    dodavatel: '',
    faktura: '',
    ean: '',
    p_kod: '',
    datum_odeslani: '',
    cislo_zasilky: '',
    poznamka: '',
    prodejna: '',
};

const ReklamaceForm = ({ defaultProdejna, onSave, onCancel }) => {
    const [form, setForm] = useState({ ...emptyForm, prodejna: defaultProdejna || '' });
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState('');
    const [showNoTrackingConfirm, setShowNoTrackingConfirm] = useState(false);

    const handleChange = (e) => {
        const { name, value } = e.target;
        setForm((prev) => ({ ...prev, [name]: value }));
        setError('');
    };

    const buildPayload = () => {
        const payload = { ...form };
        if (!payload.datum_odeslani) payload.datum_odeslani = null;
        return payload;
    };

    const submitForm = async () => {
        setSaving(true);
        setError('');
        try {
            await onSave(buildPayload());
        } catch (err) {
            const msg = err?.response?.data;
            setError(
                typeof msg === 'object'
                    ? (Object.values(msg).flat?.()?.[0] || JSON.stringify(msg))
                    : (msg || 'Uložení selhalo'),
            );
        } finally {
            setSaving(false);
            setShowNoTrackingConfirm(false);
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!form.nazev_zbozi.trim() || !form.prodejna.trim()) {
            setError('Prodejna a název zboží jsou povinné.');
            return;
        }
        if (!form.cislo_zasilky.trim()) {
            setShowNoTrackingConfirm(true);
            return;
        }
        await submitForm();
    };

    return (
        <>
            <Modal
                title="Nová reklamace"
                onClose={onCancel}
                size="md"
                bodyClassName="reklamace-form-body"
                footer={(
                    <>
                        <button type="button" className="btn-cancel" onClick={onCancel}>
                            Zrušit
                        </button>
                        <button
                            type="button"
                            className="btn-submit"
                            disabled={saving}
                            onClick={handleSubmit}
                        >
                            {saving ? 'Ukládám…' : 'Uložit'}
                        </button>
                    </>
                )}
            >
                <form className="reklamace-form" onSubmit={handleSubmit}>
                    {error && <p className="reklamace-form__error">{error}</p>}
                    <div className="reklamace-form__grid">
                        <label className="reklamace-form__full">
                            Prodejna
                            <input name="prodejna" value={form.prodejna} onChange={handleChange} required />
                        </label>
                        <label className="reklamace-form__full">
                            Název zboží
                            <input name="nazev_zbozi" value={form.nazev_zbozi} onChange={handleChange} required />
                        </label>
                        <label>
                            Dodavatel
                            <input name="dodavatel" value={form.dodavatel} onChange={handleChange} />
                        </label>
                        <label>
                            Faktura
                            <input name="faktura" value={form.faktura} onChange={handleChange} />
                        </label>
                        <label>
                            EAN
                            <input name="ean" value={form.ean} onChange={handleChange} />
                        </label>
                        <label>
                            P kód
                            <input name="p_kod" value={form.p_kod} onChange={handleChange} />
                        </label>
                        <label>
                            Datum odeslání
                            <input name="datum_odeslani" type="date" value={form.datum_odeslani} onChange={handleChange} />
                        </label>
                        <label>
                            Číslo zásilky
                            <input
                                name="cislo_zasilky"
                                value={form.cislo_zasilky}
                                onChange={handleChange}
                                placeholder="Volitelné – lze doplnit později"
                            />
                        </label>
                        <label className="reklamace-form__full">
                            Jejich označení
                            <input name="jejich_oznaceni" value={form.jejich_oznaceni} onChange={handleChange} />
                        </label>
                        <label className="reklamace-form__full">
                            Poznámka
                            <textarea name="poznamka" value={form.poznamka} onChange={handleChange} rows={2} />
                        </label>
                    </div>
                </form>
            </Modal>

            {showNoTrackingConfirm && (
                <div className="reklamace-form-confirm" role="dialog" aria-modal="true">
                    <div className="reklamace-form-confirm__box">
                        <h4>Přidat reklamaci bez čísla balíčku?</h4>
                        <p>Doplníš později / čekáš na další zboží?</p>
                        <div className="reklamace-form__actions">
                            <button
                                type="button"
                                className="btn-cancel"
                                onClick={() => setShowNoTrackingConfirm(false)}
                            >
                                Zpět – doplnit číslo
                            </button>
                            <button
                                type="button"
                                className="btn-submit"
                                disabled={saving}
                                onClick={submitForm}
                            >
                                {saving ? 'Ukládám…' : 'Ano, uložit bez čísla'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </>
    );
};

export default ReklamaceForm;
