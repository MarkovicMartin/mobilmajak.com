import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { financeAPI } from '../../services/api';
import FinanceZdrojFilter from './FinanceZdrojFilter';
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

    const zobrazeno = useMemo(
        () => (filterZdroj ? items.filter((p) => p.zdroj === filterZdroj) : items),
        [items, filterZdroj],
    );

    const setFormField = (id, field, value) => {
        setForms((prev) => ({
            ...prev,
            [id]: { ...(prev[id] || {}), [field]: value },
        }));
    };

    const handleUpload = async (polozka) => {
        const form = forms[polozka.id] || {};
        const file = form.file;
        if (!file) {
            setMessage('Vyberte soubor faktury (PDF nebo foto).');
            return;
        }
        setUploadingId(polozka.id);
        setMessage('');
        try {
            await financeAPI.uploadDoklad({
                file,
                naklad_polozka_id: polozka.id,
                cislo_faktury: form.cislo_faktury || '',
                dodavatel_nazev: form.dodavatel_nazev || '',
                castka_bez_dph: form.castka_bez_dph || '',
                dph_castka: form.dph_castka || '',
                dph_sazba: form.dph_sazba || '',
            });
            setMessage('Faktura uložena.');
            setForms((prev) => {
                const next = { ...prev };
                delete next[polozka.id];
                return next;
            });
            load();
        } catch (e) {
            setMessage(e.response?.data?.error || 'Nahrání selhalo');
        } finally {
            setUploadingId(null);
        }
    };

    return (
        <section className="finance-faktury-panel">
            {intro && <p className="finance-faktury-panel__intro">{intro}</p>}
            <p className="finance-faktury-panel__hint">
                Výdej z pokladny se sem dostane po nočním importu (cca 22:00).
                Prodejna je doplněná automaticky podle pokladny, kde byl výběr proveden.
            </p>
            {loading && <p>Načítám…</p>}
            {error && <p className="finance-faktury-error">{error}</p>}
            {message && <p className="finance-faktury-message">{message}</p>}
            {!loading && items.length > 0 && (
                <FinanceZdrojFilter
                    value={filterZdroj}
                    onChange={setFilterZdroj}
                    items={items}
                />
            )}
            {!loading && zobrazeno.length === 0 && (
                <p className="finance-faktury-empty">Žádné výdaje nečekají na fakturu.</p>
            )}
            {!loading && zobrazeno.length > 0 && (
                <div className="finance-faktury-list">
                    {zobrazeno.map((p) => {
                        const src = zdrojMeta(p.zdroj);
                        return (
                        <article key={p.id} className={`finance-faktury-card ${src.rowClass}`}>
                            <div className="finance-faktury-card__head">
                                <span className={`finance-badge ${src.badgeClass}`}>{src.label}</span>
                                <span>{p.datum}</span>
                                <strong>{formatCurrency(p.castka)}</strong>
                            </div>
                            <p className="finance-faktury-card__text">{movementLabel(p)}</p>
                            {p.prodejna_nazev && (
                                <p className="finance-faktury-card__meta">Prodejna: {p.prodejna_nazev}</p>
                            )}
                            {p.kategorie_nazev && (
                                <p className="finance-faktury-card__meta">Kategorie: {p.kategorie_nazev}</p>
                            )}
                            <div className="finance-faktury-upload">
                                <label>
                                    Faktura (PDF, JPG, PNG)
                                    <input
                                        type="file"
                                        accept=".pdf,.jpg,.jpeg,.png,.webp,image/*,application/pdf"
                                        onChange={(e) => setFormField(
                                            p.id,
                                            'file',
                                            e.target.files?.[0] || null,
                                        )}
                                    />
                                </label>
                                <div className="finance-faktury-upload__optional">
                                    <input
                                        type="text"
                                        placeholder="Číslo faktury (volitelné)"
                                        value={forms[p.id]?.cislo_faktury || ''}
                                        onChange={(e) => setFormField(p.id, 'cislo_faktury', e.target.value)}
                                    />
                                    <input
                                        type="text"
                                        placeholder="Dodavatel (volitelné)"
                                        value={forms[p.id]?.dodavatel_nazev || ''}
                                        onChange={(e) => setFormField(p.id, 'dodavatel_nazev', e.target.value)}
                                    />
                                    <input
                                        type="text"
                                        placeholder="Základ bez DPH (volitelné)"
                                        value={forms[p.id]?.castka_bez_dph || ''}
                                        onChange={(e) => setFormField(p.id, 'castka_bez_dph', e.target.value)}
                                    />
                                    <input
                                        type="text"
                                        placeholder="DPH (volitelné)"
                                        value={forms[p.id]?.dph_castka || ''}
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
                        </article>
                        );
                    })}
                </div>
            )}
        </section>
    );
};

export default FinanceFakturyPanel;
