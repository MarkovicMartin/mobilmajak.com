import React, { useState, useEffect } from 'react';
import { ZPUSOB_VYRIzeni_OPTIONS } from './constants';
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
    zpusob_vyrizeni: '',
    datum_vyrizeni: '',
    sklad_vyskladneno: false,
    sklad_naskladneno: false,
};

const ReklamaceForm = ({ initial, defaultProdejna, onSave, onCancel }) => {
    const [form, setForm] = useState({ ...emptyForm, prodejna: defaultProdejna });
    const [saving, setSaving] = useState(false);
    const [showNoTrackingConfirm, setShowNoTrackingConfirm] = useState(false);

    useEffect(() => {
        if (initial) {
            setForm({
                ...emptyForm,
                ...initial,
                datum_odeslani: initial.datum_odeslani || '',
                datum_vyrizeni: initial.datum_vyrizeni || '',
                sklad_vyskladneno: Boolean(initial.sklad_vyskladneno),
                sklad_naskladneno: Boolean(initial.sklad_naskladneno),
            });
        }
    }, [initial]);

    const handleChange = (e) => {
        const { name, value, type, checked } = e.target;
        setForm((prev) => ({
            ...prev,
            [name]: type === 'checkbox' ? checked : value,
        }));
    };

    const buildPayload = () => {
        const payload = { ...form };
        if (!payload.datum_odeslani) payload.datum_odeslani = null;
        if (!payload.datum_vyrizeni) payload.datum_vyrizeni = null;
        if (!payload.zpusob_vyrizeni) payload.zpusob_vyrizeni = '';
        return payload;
    };

    const submitForm = async () => {
        setSaving(true);
        try {
            await onSave(buildPayload());
        } finally {
            setSaving(false);
            setShowNoTrackingConfirm(false);
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        const isCreate = !initial;
        const missingTracking = !form.cislo_zasilky.trim();
        if (isCreate && missingTracking) {
            setShowNoTrackingConfirm(true);
            return;
        }
        await submitForm();
    };

    return (
        <div className="reklamace-form-overlay">
            <form className="reklamace-form" onSubmit={handleSubmit}>
                <h3>{initial ? 'Upravit reklamaci' : 'Nová reklamace'}</h3>
                <div className="reklamace-form__grid">
                    {initial && (
                        <label>Naše značka
                            <input name="nase_znacka" value={initial.nase_znacka} readOnly disabled />
                        </label>
                    )}
                    <label className={initial ? '' : 'reklamace-form__full'}>Prodejna
                        <input name="prodejna" value={form.prodejna} onChange={handleChange} required />
                    </label>
                    <label className="reklamace-form__full">Název zboží<input name="nazev_zbozi" value={form.nazev_zbozi} onChange={handleChange} required /></label>
                    <label>Dodavatel<input name="dodavatel" value={form.dodavatel} onChange={handleChange} /></label>
                    <label>Faktura<input name="faktura" value={form.faktura} onChange={handleChange} /></label>
                    <label>EAN<input name="ean" value={form.ean} onChange={handleChange} /></label>
                    <label>P kód<input name="p_kod" value={form.p_kod} onChange={handleChange} /></label>
                    <label>Datum odeslání<input name="datum_odeslani" type="date" value={form.datum_odeslani} onChange={handleChange} /></label>
                    <label>Číslo zásilky<input name="cislo_zasilky" value={form.cislo_zasilky} onChange={handleChange} placeholder="Volitelné – lze doplnit později" /></label>
                    <label className="reklamace-form__full">Poznámka<textarea name="poznamka" value={form.poznamka} onChange={handleChange} rows={2} /></label>
                    {initial && (
                        <>
                            <label>Způsob vyřízení
                                <select name="zpusob_vyrizeni" value={form.zpusob_vyrizeni} onChange={handleChange}>
                                    <option value="">—</option>
                                    {ZPUSOB_VYRIzeni_OPTIONS.map((o) => (
                                        <option key={o.value} value={o.value}>{o.label}</option>
                                    ))}
                                </select>
                            </label>
                            <label>Datum vyřízení<input name="datum_vyrizeni" type="date" value={form.datum_vyrizeni} onChange={handleChange} /></label>
                            <label className="reklamace-form__checkbox" title="Připraveno pro budoucí Symplio vyskladnění">
                                <input name="sklad_vyskladneno" type="checkbox" checked={form.sklad_vyskladneno} onChange={handleChange} />
                                Vyskladněno
                            </label>
                            <label className="reklamace-form__checkbox" title="Připraveno pro budoucí Symplio naskladnění">
                                <input name="sklad_naskladneno" type="checkbox" checked={form.sklad_naskladneno} onChange={handleChange} />
                                Naskladněno
                            </label>
                        </>
                    )}
                </div>
                <div className="reklamace-form__actions">
                    <button type="button" className="btn btn-outline" onClick={onCancel}>Zrušit</button>
                    <button type="submit" className="btn btn-primary" disabled={saving}>{saving ? 'Ukládám…' : 'Uložit'}</button>
                </div>
            </form>

            {showNoTrackingConfirm && (
                <div className="reklamace-form-confirm" role="dialog" aria-modal="true">
                    <div className="reklamace-form-confirm__box">
                        <h4>Přidat reklamaci bez čísla balíčku?</h4>
                        <p>Doplníš později / čekáš na další zboží?</p>
                        <div className="reklamace-form__actions">
                            <button
                                type="button"
                                className="btn btn-outline"
                                onClick={() => setShowNoTrackingConfirm(false)}
                            >
                                Zpět – doplnit číslo
                            </button>
                            <button
                                type="button"
                                className="btn btn-primary"
                                disabled={saving}
                                onClick={submitForm}
                            >
                                {saving ? 'Ukládám…' : 'Ano, uložit bez čísla'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default ReklamaceForm;
