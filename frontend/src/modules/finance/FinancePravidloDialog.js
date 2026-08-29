import React, { useEffect, useState } from 'react';
import { financeAPI } from '../../services/api';
import './FinanceModule.css';

const emptyForm = {
    protiucet: '',
    zprava_obsahuje: '',
    text_shoda: 'obsahuje',
    vs: '',
    kategorie_id: '',
    prodejna_id: '',
    ignorovat: false,
};

const fromNavrh = (navrh) => ({
    protiucet: navrh?.protiucet || '',
    zprava_obsahuje: navrh?.zprava_obsahuje || '',
    text_shoda: navrh?.text_shoda || 'obsahuje',
    vs: navrh?.vs || '',
    kategorie_id: navrh?.kategorie_id ? String(navrh.kategorie_id) : '',
    prodejna_id: navrh?.prodejna_id ? String(navrh.prodejna_id) : '',
    ignorovat: !!navrh?.ignorovat,
});

const formatPreviewDate = (value) => {
    if (!value) return '–';
    return String(value).slice(0, 10);
};

const formatCurrency = (value) => {
    const n = Number(value) || 0;
    return new Intl.NumberFormat('cs-CZ', {
        style: 'currency',
        currency: 'CZK',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
    }).format(Math.round(n));
};

/**
 * Po zařazení / ignorování: chceš vytvořit pravidlo? Předvyplněný formulář.
 */
const FinancePravidloDialog = ({
    open,
    mode = 'zaradit',
    polozka,
    navrhPayload,
    kategorie = [],
    stores = [],
    keepKatDefault = true,
    onSkip,
    onConfirmIgnore,
}) => {
    const isIgnore = mode === 'ignorovat';
    const [step, setStep] = useState(isIgnore ? 'ignore' : 'ask');
    const [keepKat, setKeepKat] = useState(keepKatDefault);
    const [form, setForm] = useState(emptyForm);
    const [navrh, setNavrh] = useState(navrhPayload);
    const [preview, setPreview] = useState(null);
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState('');

    useEffect(() => {
        if (!open) return;
        setStep(isIgnore ? 'ignore' : 'ask');
        setKeepKat(keepKatDefault);
        setNavrh(navrhPayload);
        setForm(fromNavrh(navrhPayload?.navrh));
        setPreview(null);
        setError('');
    }, [open, isIgnore, keepKatDefault, navrhPayload, polozka?.id]);

    if (!open || !polozka) return null;

    const varovani = navrh?.varovani;
    const varovaniText = varovani === 'fio_bez_uctu'
        ? 'U této Fio platby chybí číslo účtu (v protiúčtu je pravděpodobně VS). Doplň účet ručně, nebo pravidlo přeskoč.'
        : varovani === 'chybi_popis'
            ? 'Chybí popisek pro pravidlo z kasy. Doplň text, nebo přeskoč.'
            : '';

    const setField = (field, value) => {
        setForm((prev) => ({ ...prev, [field]: value }));
    };

    const close = () => {
        onSkip?.();
    };

    const goToForm = (payload) => {
        const next = payload || navrh;
        setNavrh(next);
        setForm(fromNavrh({
            ...(next?.navrh || {}),
            ignorovat: isIgnore || next?.navrh?.ignorovat,
        }));
        setStep('form');
    };

    const handleAskYes = () => goToForm(navrh);

    const handleIgnoreConfirm = async (wantRule) => {
        if (!onConfirmIgnore) return;
        setBusy(true);
        setError('');
        try {
            const res = await onConfirmIgnore({ keepKat, wantRule });
            if (wantRule) {
                goToForm(res?.pravidlo_navrh || navrh);
            } else {
                close();
            }
        } catch (e) {
            setError(e.response?.data?.error || e.message || 'Ignorování selhalo');
        } finally {
            setBusy(false);
        }
    };

    const loadPreview = async () => {
        setBusy(true);
        setError('');
        try {
            const res = await financeAPI.previewPravidlo({
                scope: 'nezarazene',
                limit: 50,
                protiucet: form.protiucet,
                zprava_obsahuje: form.zprava_obsahuje,
                text_shoda: form.text_shoda,
                vs: form.vs,
                kategorie_id: form.kategorie_id || null,
                ignorovat: form.ignorovat,
            });
            setPreview(res);
        } catch (e) {
            setError(e.response?.data?.error || 'Náhled selhal');
        } finally {
            setBusy(false);
        }
    };

    const saveRule = async () => {
        if (!form.protiucet.trim() && !form.zprava_obsahuje.trim() && !form.vs.trim()) {
            setError('Doplň protiúčet nebo text zprávy.');
            return;
        }
        setBusy(true);
        setError('');
        try {
            await financeAPI.createPravidloFromPolozka({
                polozka_id: polozka.id,
                protiucet: form.protiucet,
                zprava_obsahuje: form.zprava_obsahuje,
                text_shoda: form.text_shoda,
                vs: form.vs,
                kategorie_id: form.kategorie_id || null,
                prodejna_id: form.prodejna_id || null,
                ignorovat: isIgnore || form.ignorovat,
            });
            close();
        } catch (e) {
            setError(e.response?.data?.error || 'Uložení pravidla selhalo');
        } finally {
            setBusy(false);
        }
    };

    const title = isIgnore
        ? 'Ignorovat platbu'
        : 'Vytvořit pravidlo ze zařazení';

    return (
        <div className="finance-modal-backdrop" role="presentation" onClick={close}>
            <div
                className="finance-modal"
                role="dialog"
                aria-labelledby="finance-pravidlo-title"
                onClick={(e) => e.stopPropagation()}
            >
                <h3 id="finance-pravidlo-title">{title}</h3>
                {error && <p className="finance-error">{error}</p>}

                {step === 'ignore' && (
                    <>
                        <p>Platba se nepočítá do nákladů. Kategorie může zůstat.</p>
                        <label className="finance-checkbox-label">
                            <input
                                type="checkbox"
                                checked={keepKat}
                                onChange={(e) => setKeepKat(e.target.checked)}
                            />
                            Ponechat kategorii
                        </label>
                        <div className="finance-modal__actions">
                            <button
                                type="button"
                                className="finance-btn-primary"
                                disabled={busy}
                                onClick={() => handleIgnoreConfirm(false)}
                            >
                                Jen tuhle platbu
                            </button>
                            <button
                                type="button"
                                className="finance-btn-secondary"
                                disabled={busy}
                                onClick={() => handleIgnoreConfirm(true)}
                            >
                                Vytvořit pravidlo ignorovat
                            </button>
                            <button type="button" disabled={busy} onClick={close}>Zrušit</button>
                        </div>
                    </>
                )}

                {step === 'ask' && (
                    <>
                        <p>Chceš ze zařazení vytvořit pravidlo pro další podobné platby?</p>
                        <div className="finance-modal__actions">
                            <button type="button" className="finance-btn-primary" onClick={handleAskYes}>
                                Ano, navrhnout pravidlo
                            </button>
                            <button type="button" className="finance-btn-secondary" onClick={close}>
                                Ne, jen tahle platba
                            </button>
                        </div>
                    </>
                )}

                {step === 'form' && (
                    <>
                        {varovaniText && <p className="finance-doklad-edit__warn">{varovaniText}</p>}
                        <p className="finance-modal__hint">
                            {navrh?.zdroj_logika === 'fio'
                                ? 'Fio: klíčem je číslo protiúčtu.'
                                : 'Pokladna: klíčem je popisek výdeje.'}
                        </p>
                        <div className="finance-form finance-form--wide">
                            <label>
                                Protiúčet
                                <input
                                    type="text"
                                    value={form.protiucet}
                                    onChange={(e) => setField('protiucet', e.target.value)}
                                />
                            </label>
                            <label>
                                Text zprávy / popisu
                                <input
                                    type="text"
                                    value={form.zprava_obsahuje}
                                    onChange={(e) => setField('zprava_obsahuje', e.target.value)}
                                />
                            </label>
                            <label>
                                Shoda textu
                                <select
                                    value={form.text_shoda}
                                    onChange={(e) => setField('text_shoda', e.target.value)}
                                >
                                    <option value="obsahuje">Obsahuje</option>
                                    <option value="presne">Přesně</option>
                                </select>
                            </label>
                            <label>
                                Kategorie
                                <select
                                    value={form.kategorie_id}
                                    onChange={(e) => setField('kategorie_id', e.target.value)}
                                >
                                    <option value="">— bez —</option>
                                    {kategorie.map((k) => (
                                        <option key={k.id} value={k.id}>{k.nazev}</option>
                                    ))}
                                </select>
                            </label>
                            {stores.length > 0 && (
                                <label>
                                    Prodejna
                                    <select
                                        value={form.prodejna_id}
                                        onChange={(e) => setField('prodejna_id', e.target.value)}
                                    >
                                        <option value="">— bez —</option>
                                        {stores.map((s) => (
                                            <option key={s.id} value={s.id}>{s.nazev || s.label}</option>
                                        ))}
                                    </select>
                                </label>
                            )}
                            <label className="finance-checkbox-label">
                                <input
                                    type="checkbox"
                                    checked={form.ignorovat}
                                    onChange={(e) => setField('ignorovat', e.target.checked)}
                                    disabled={isIgnore}
                                />
                                Ignorovat (nepočítat do nákladů)
                            </label>
                        </div>
                        {preview && (
                            <p className="finance-rule-preview__stats">
                                Nezařazených shod: <strong>{preview.total ?? 0}</strong>
                                {(preview.polozky || []).slice(0, 3).map((p) => (
                                    <span key={p.id}> · {formatPreviewDate(p.datum)} {formatCurrency(p.castka)}</span>
                                ))}
                            </p>
                        )}
                        <div className="finance-modal__actions">
                            <button
                                type="button"
                                className="finance-btn-primary"
                                disabled={busy}
                                onClick={saveRule}
                            >
                                Uložit pravidlo
                            </button>
                            <button
                                type="button"
                                className="finance-btn-secondary"
                                disabled={busy}
                                onClick={loadPreview}
                            >
                                Náhled shod
                            </button>
                            <button type="button" disabled={busy} onClick={close}>Přeskočit</button>
                        </div>
                    </>
                )}
            </div>
        </div>
    );
};

export default FinancePravidloDialog;
