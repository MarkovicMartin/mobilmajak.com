import React, { useCallback, useEffect, useState } from 'react';
import { financeAPI } from '../../services/api';
import FinanceDropZone from './FinanceDropZone';
import './FinanceFakturyPanel.css';
import './FinanceKontrolaPanel.css';

const formatCurrency = (value) => {
    const n = Number(value);
    if (!Number.isFinite(n)) return '–';
    return new Intl.NumberFormat('cs-CZ', {
        style: 'currency',
        currency: 'CZK',
        minimumFractionDigits: 2,
    }).format(n);
};

const fromRow = (row) => ({
    cislo_faktury: row?.cislo_faktury || '',
    datum_vystaveni: row?.datum_vystaveni || '',
    castka_celkem: row?.castka_celkem != null ? String(row.castka_celkem) : '',
    dph_castka: row?.dph_castka != null ? String(row.dph_castka) : '0',
    vs: row?.vs || '',
});

const ReviewCard = ({ row, busy, onSave, onFlexi }) => {
    const [form, setForm] = useState(() => fromRow(row));

    useEffect(() => {
        setForm(fromRow(row));
    }, [row.id, row.cislo_faktury, row.datum_vystaveni, row.castka_celkem, row.dph_castka, row.vs]);

    const setField = (field, value) => setForm((prev) => ({ ...prev, [field]: value }));
    const chyby = Array.isArray(row.ocr_chyby) ? row.ocr_chyby.filter(Boolean) : [];
    const flexi = row.flexi || {};

    return (
        <article className="finance-kontrola-card">
            <header className="finance-kontrola-card__head">
                <strong>{row.cislo_faktury || 'Číslo nevyčteno'}</strong>
                <span>{formatCurrency(row.castka_celkem)}</span>
                <span>{row.datum_vystaveni || 'bez data'}</span>
                {row.soubor_url && (
                    <a href={row.soubor_url} target="_blank" rel="noopener noreferrer">
                        {row.soubor_nazev || 'Soubor'}
                    </a>
                )}
            </header>
            {chyby.length > 0 && <p className="finance-error">{chyby.join(' ')}</p>}
            {flexi.error && !flexi.ok && <p className="finance-error">{flexi.error}</p>}
            <form
                className="finance-form finance-form--wide"
                onSubmit={(e) => {
                    e.preventDefault();
                    onSave(row.id, form);
                }}
            >
                <label>
                    Číslo dokladu
                    <input
                        type="text"
                        value={form.cislo_faktury}
                        onChange={(e) => setField('cislo_faktury', e.target.value)}
                        disabled={busy}
                    />
                </label>
                <label>
                    Datum vystavení
                    <input
                        type="date"
                        value={form.datum_vystaveni}
                        onChange={(e) => setField('datum_vystaveni', e.target.value)}
                        disabled={busy}
                    />
                </label>
                <label>
                    Dobropisovaná částka
                    <input
                        type="text"
                        inputMode="decimal"
                        value={form.castka_celkem}
                        onChange={(e) => setField('castka_celkem', e.target.value)}
                        disabled={busy}
                    />
                </label>
                <label>
                    DPH
                    <input
                        type="text"
                        inputMode="decimal"
                        value={form.dph_castka}
                        onChange={(e) => setField('dph_castka', e.target.value)}
                        disabled={busy}
                    />
                </label>
                <label>
                    VS
                    <input
                        type="text"
                        value={form.vs}
                        onChange={(e) => setField('vs', e.target.value)}
                        disabled={busy}
                    />
                </label>
                <div className="finance-kontrola-actions">
                    <button type="submit" className="finance-btn-secondary" disabled={busy}>
                        Uložit údaje
                    </button>
                    <button
                        type="button"
                        className="finance-btn-primary"
                        disabled={busy}
                        onClick={() => onFlexi(row.id, form)}
                    >
                        {busy ? 'Zapisuji…' : 'Zapsat do Flexi'}
                    </button>
                </div>
            </form>
        </article>
    );
};

const FinanceDobropisyPanel = () => {
    const [rows, setRows] = useState([]);
    const [loading, setLoading] = useState(true);
    const [uploading, setUploading] = useState(false);
    const [busyId, setBusyId] = useState(null);
    const [error, setError] = useState('');
    const [message, setMessage] = useState('');

    const load = useCallback(async () => {
        setLoading(true);
        try {
            const data = await financeAPI.getDobropisy();
            setRows(Array.isArray(data) ? data : []);
        } catch (e) {
            setError(e.response?.data?.error || e.message || 'Chyba načítání dobropisů');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        load();
    }, [load]);

    const uploadFiles = async (files) => {
        if (!files?.length) return;
        setUploading(true);
        setError('');
        setMessage('');
        try {
            const data = await financeAPI.uploadDobropisy(files);
            const n = data?.doklady?.length || 0;
            const chyby = Array.isArray(data?.chyby) ? data.chyby : [];
            const fail = chyby.map((c) => `${c.soubor}: ${c.error}`).join(' ');
            setMessage(n
                ? `Vyčteno ${n} ${n === 1 ? 'dobropis' : n < 5 ? 'dobropisy' : 'dobropisů'}. Zkontrolujte částky a pak je zapište do Flexi.`
                : 'Nic nového se neuložilo.');
            if (fail) setError(fail);
            load();
        } catch (e) {
            const data = e.response?.data;
            const chyby = Array.isArray(data?.chyby) ? data.chyby : [];
            setError(chyby.map((c) => `${c.soubor}: ${c.error}`).join(' ') || data?.error || e.message || 'Nahrání selhalo');
        } finally {
            setUploading(false);
        }
    };

    const payloadFromForm = (form) => ({
        cislo_faktury: form.cislo_faktury,
        datum_vystaveni: form.datum_vystaveni,
        castka_celkem: form.castka_celkem,
        castka_bez_dph: form.castka_celkem,
        dph_castka: form.dph_castka,
        dph_sazba: form.dph_castka === '' || Number(String(form.dph_castka).replace(',', '.')) === 0 ? '0' : '',
        vs: form.vs,
    });

    const save = async (id, form) => {
        setBusyId(id);
        setError('');
        setMessage('');
        try {
            await financeAPI.updateDoklad(id, payloadFromForm(form));
            setMessage('Údaje uloženy.');
            load();
        } catch (e) {
            setError(e.response?.data?.error || e.message || 'Uložení selhalo');
        } finally {
            setBusyId(null);
        }
    };

    const zapsat = async (id, form) => {
        setBusyId(id);
        setError('');
        setMessage('');
        try {
            await financeAPI.updateDoklad(id, payloadFromForm(form));
            const data = await financeAPI.odeslatDobropisFlexi(id);
            const kod = data?.flexi?.flexi_kod || data?.flexi_id;
            setMessage(kod ? `Ve Flexi vznikl doklad ${kod}.` : 'Zapsáno do Flexi.');
            load();
        } catch (e) {
            setError(e.response?.data?.error || e.message || 'Zápis do Flexi selhal');
            load();
        } finally {
            setBusyId(null);
        }
    };

    const ceka = rows.filter((row) => row.stav !== 'odeslano_flexi');
    const hotovo = rows.filter((row) => row.stav === 'odeslano_flexi');

    return (
        <section className="finance-panel">
            <p className="finance-panel__intro">
                Nahrajte víc dobropisů Partnertele naráz. Vyčte se číslo dokladu, datum a částka k úhradě.
                Do Flexi se zapíše až po kontrole.
            </p>
            <div className="finance-kontrola-upload">
                <FinanceDropZone
                    multiple
                    disabled={uploading}
                    label={uploading ? 'Vyčítám…' : 'Přetáhněte dobropisy sem nebo vyberte víc souborů'}
                    onFiles={uploadFiles}
                />
            </div>
            {error && <p className="finance-error">{error}</p>}
            {message && <p className="finance-message">{message}</p>}
            {loading && <p className="finance-loading">Načítám dobropisy…</p>}

            {!loading && ceka.length === 0 && (
                <p className="finance-empty">Žádný dobropis nečeká na kontrolu.</p>
            )}
            <div className="finance-kontrola-list">
                {ceka.map((row) => (
                    <ReviewCard
                        key={row.id}
                        row={row}
                        busy={busyId === row.id}
                        onSave={save}
                        onFlexi={zapsat}
                    />
                ))}
            </div>

            {hotovo.length > 0 && (
                <div className="finance-table-wrap">
                    <h3 className="finance-faktury-section-title">Zapsané ve Flexi</h3>
                    <table className="finance-table">
                        <thead>
                            <tr>
                                <th>Datum</th>
                                <th>Číslo</th>
                                <th>Částka</th>
                                <th>Flexi</th>
                            </tr>
                        </thead>
                        <tbody>
                            {hotovo.map((row) => (
                                <tr key={row.id}>
                                    <td>{row.datum_vystaveni || '–'}</td>
                                    <td>{row.cislo_faktury}</td>
                                    <td>{formatCurrency(row.castka_celkem)}</td>
                                    <td>{row.flexi?.flexi_kod || row.flexi_id || '–'}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </section>
    );
};

export default FinanceDobropisyPanel;
