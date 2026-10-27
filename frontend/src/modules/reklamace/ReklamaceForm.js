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
        if (saving) return;
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
        if (saving) return;
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
                onClose={showNoTrackingConfirm ? undefined : onCancel}
                closeOnBackdrop={!showNoTrackingConfirm}
                size="md"
                bodyClassName="reklamace-form-body"
                footer={(
                    <>
                        <button type="button" className="btn-cancel" onClick={onCancel} disabled={saving}>
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
                <Modal
                    title="Přidat reklamaci bez čísla balíčku?"
                    onClose={() => {
                        if (!saving) setShowNoTrackingConfirm(false);
                    }}
                    size="sm"
                    overlayClassName="reklamace-form-confirm-overlay"
                    footer={(
                        <>
                            <button
                                type="button"
                                className="btn-cancel"
                                disabled={saving}
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
                        </>
                    )}
                >
                    <p className="reklamace-form-confirm__text">
                        Doplníš později / čekáš na další zboží?
                    </p>
                </Modal>
            )}
        </>
    );
};

export default ReklamaceForm;
