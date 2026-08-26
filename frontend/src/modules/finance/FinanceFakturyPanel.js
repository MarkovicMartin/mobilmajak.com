import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { financeAPI } from '../../services/api';
import FinanceZdrojFilter from './FinanceZdrojFilter';
import FinanceDropZone from './FinanceDropZone';
import FinanceDokladSummary from './FinanceDokladSummary';
import { movementLabel, zdrojMeta } from './financeUtils';
import './FinanceFakturyPanel.css';

const formatCurrency = (value) => {
    const n = Number(value) || 0;
    return new Intl.NumberFormat('cs-CZ', {
        style: 'currency',
        currency: 'CZK',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
    }).format(Math.round(n));
};

const FinanceFakturyPanel = ({ intro }) => {
    const [items, setItems] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [message, setMessage] = useState('');
    const [uploadingId, setUploadingId] = useState(null);
    const [forms, setForms] = useState({});
    const [filterZdroj, setFilterZdroj] = useState('');
    /** Položky právě nahrané v této relaci – držíme kartu s OCR shrnutím. */
    const [doneUploads, setDoneUploads] = useState([]);

    const load = useCallback(async () => {
        setLoading(true);
        setError('');
        try {
            const rows = await financeAPI.getCekaNaFakturu();
            setItems(Array.isArray(rows) ? rows : []);
        } catch (e) {
            setError(e.response?.data?.error || e.message || 'Chyba načítání');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        load();
    }, [load]);

    const waiting = useMemo(
        () => (filterZdroj ? items.filter((p) => p.zdroj === filterZdroj) : items),
        [items, filterZdroj],
    );

    const doneFiltered = useMemo(
        () => (filterZdroj ? doneUploads.filter((p) => p.zdroj === filterZdroj) : doneUploads),
        [doneUploads, filterZdroj],
    );

    const hintDefaults = (p) => {
        const h = p.faktura_hint;
        if (!h) return {};
        return {
            dodavatel_nazev: h.dodavatel_nazev || '',
            cislo_faktury: h.cislo_faktury || '',
        };
    };

    const formFor = (p) => ({ ...hintDefaults(p), ...(forms[p.id] || {}) });

    const setFormField = (id, field, value) => {
        setForms((prev) => ({
            ...prev,
            [id]: { ...(prev[id] || {}), [field]: value },
        }));
    };

    const handleUpload = async (polozka) => {
        const form = formFor(polozka);
        const file = form.file;
        if (!file) {
            setMessage('Vyberte soubor faktury (PDF nebo foto).');
            return;
        }
        setUploadingId(polozka.id);
        setMessage('');
        try {
            const result = await financeAPI.uploadDoklad({
                file,
                naklad_polozka_id: polozka.id,
                cislo_faktury: form.cislo_faktury || '',
                dodavatel_nazev: form.dodavatel_nazev || '',
                castka_bez_dph: form.castka_bez_dph || '',
                dph_castka: form.dph_castka || '',
                dph_sazba: form.dph_sazba || '',
            });
            setMessage('Faktura uložena – OCR vyčetlo údaje níže.');
            setForms((prev) => {
                const next = { ...prev };
                delete next[polozka.id];
                return next;
            });
            setDoneUploads((prev) => [
                {
                    ...polozka,
                    doklad_id: result?.doklad?.id || polozka.doklad_id,
                    doklad: result?.doklad || null,
                    _justUploaded: true,
                },
                ...prev.filter((x) => x.id !== polozka.id),
            ]);
            load();
        } catch (e) {
            setMessage(e.response?.data?.error || 'Nahrání selhalo');
        } finally {
            setUploadingId(null);
        }
    };

    const renderCard = (p, { uploaded = false } = {}) => {
        const src = zdrojMeta(p.zdroj, p.pokladna_label);
        const form = formFor(p);
        return (
            <article
                key={p.id}
                className={`finance-faktury-card ${src.rowClass}${uploaded ? ' finance-faktury-card--done' : ''}`}
            >
                <div className="finance-faktury-card__head">
                    <span className={`finance-badge ${src.badgeClass}`}>{src.label}</span>
                    <span>{p.datum}</span>
                    <strong>{formatCurrency(p.castka)}</strong>
                </div>
                <p className="finance-faktury-card__text">{movementLabel(p)}</p>
                {p.faktura_hint && !uploaded && (
                    <p className="finance-faktury-card__parsed">
                        Rozpoznáno z pokladny:{' '}
                        <strong>{p.faktura_hint.dodavatel_nazev}</strong>
                        {', FA '}
                        <strong>{p.faktura_hint.cislo_faktury}</strong>
                        {p.faktura_hint.castka_celkem && (
                            <>, {formatCurrency(p.faktura_hint.castka_celkem)}</>
                        )}
                    </p>
                )}
                {p.prodejna_nazev && (
                    <p className="finance-faktury-card__meta">Prodejna: {p.prodejna_nazev}</p>
                )}
                {p.kategorie_nazev && (
                    <p className="finance-faktury-card__meta">Kategorie: {p.kategorie_nazev}</p>
                )}
                {uploaded ? (
                    <FinanceDokladSummary doklad={p.doklad} />
                ) : (
                    <div className="finance-faktury-upload">
                        <FinanceDropZone
                            compact={Boolean(p.faktura_hint)}
                            disabled={uploadingId === p.id}
                            label="Přetáhněte fakturu sem (PDF / foto)"
                            onFile={(file) => setFormField(p.id, 'file', file)}
                        />
                        {form.file && (
                            <p className="finance-faktury-file-name">
                                Vybráno: {form.file.name}
                            </p>
                        )}
                        <div className="finance-faktury-upload__optional">
                            <input
                                type="text"
                                placeholder="Číslo faktury"
                                value={form.cislo_faktury || ''}
                                onChange={(e) => setFormField(p.id, 'cislo_faktury', e.target.value)}
                            />
                            <input
                                type="text"
                                placeholder="Dodavatel"
                                value={form.dodavatel_nazev || ''}
                                onChange={(e) => setFormField(p.id, 'dodavatel_nazev', e.target.value)}
                            />
                            <input
                                type="text"
                                placeholder="Základ bez DPH (z FA / OCR)"
                                value={form.castka_bez_dph || ''}
                                onChange={(e) => setFormField(p.id, 'castka_bez_dph', e.target.value)}
                            />
                            <input
                                type="text"
                                placeholder="DPH (z FA / OCR)"
                                value={form.dph_castka || ''}
                                onChange={(e) => setFormField(p.id, 'dph_castka', e.target.value)}
                            />
                        </div>
                        <button
                            type="button"
                            disabled={uploadingId === p.id}
                            onClick={() => handleUpload(p)}
                        >
                            {uploadingId === p.id ? 'Nahrávám…' : 'Přiložit fakturu'}
                        </button>
                    </div>
                )}
            </article>
        );
    };

    const empty = !loading && waiting.length === 0 && doneFiltered.length === 0;

    return (
        <section className="finance-faktury-panel">
            {intro && <p className="finance-faktury-panel__intro">{intro}</p>}
            <p className="finance-faktury-panel__hint">
                Výdej z pokladny se sem dostane během dne (import ze Symplio cca každých
                30&nbsp;min mezi 8:30–21:00). Prodejna je podle pokladny, kde byl výběr.
            </p>
            {loading && <p>Načítám…</p>}
            {error && <p className="finance-faktury-error">{error}</p>}
            {message && <p className="finance-faktury-message">{message}</p>}
            {!loading && (items.length > 0 || doneUploads.length > 0) && (
                <FinanceZdrojFilter
                    value={filterZdroj}
                    onChange={setFilterZdroj}
                    items={[...items, ...doneUploads]}
                />
            )}
            {empty && (
                <p className="finance-faktury-empty">Žádné výdaje nečekají na fakturu.</p>
            )}
            {!loading && doneFiltered.length > 0 && (
                <div className="finance-faktury-list">
                    <h3 className="finance-faktury-section-title">Právě nahrané</h3>
                    {doneFiltered.map((p) => renderCard(p, { uploaded: true }))}
                </div>
            )}
            {!loading && waiting.length > 0 && (
                <div className="finance-faktury-list">
                    {doneFiltered.length > 0 && (
                        <h3 className="finance-faktury-section-title">Čeká na fakturu</h3>
                    )}
                    {waiting.map((p) => renderCard(p))}
                </div>
            )}
        </section>
    );
};

export default FinanceFakturyPanel;
