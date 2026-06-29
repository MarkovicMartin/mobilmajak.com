import React, { useCallback, useEffect, useState } from 'react';
import { PageHeader } from '../../components/ui';
import { financeAPI, storeAPI } from '../../services/api';
import './FinanceModule.css';

const formatCurrency = (value) => {
    const n = Number(value) || 0;
    return new Intl.NumberFormat('cs-CZ', {
        style: 'currency',
        currency: 'CZK',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
    }).format(Math.round(n));
};

const FinanceModule = () => {
    const [tab, setTab] = useState('k-zarazeni');
    const [status, setStatus] = useState(null);
    const [kategorie, setKategorie] = useState([]);
    const [stores, setStores] = useState([]);
    const [nezarazene, setNezarazene] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [message, setMessage] = useState('');

    const [manualForm, setManualForm] = useState({
        datum: new Date().toISOString().slice(0, 10),
        castka: '',
        kategorie_id: '',
        prodejna_id: '',
        popis: '',
        poznamka_admin: '',
    });

    const loadAll = useCallback(async () => {
        setLoading(true);
        setError('');
        try {
            const [st, kat, nz, storeChoices] = await Promise.all([
                financeAPI.getStatus(),
                financeAPI.getKategorie(),
                financeAPI.getNezarazene(),
                storeAPI.getStoreChoices(),
            ]);
            setStatus(st);
            setKategorie(Array.isArray(kat) ? kat : []);
            setNezarazene(Array.isArray(nz) ? nz : []);
            const list = Array.isArray(storeChoices) ? storeChoices : storeChoices?.results || [];
            setStores(list);
        } catch (e) {
            setError(e.response?.data?.error || e.message || 'Chyba načítání');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        loadAll();
    }, [loadAll]);

    const handleManualSubmit = async (e) => {
        e.preventDefault();
        setMessage('');
        try {
            await financeAPI.createManualNaklad({
                ...manualForm,
                castka: manualForm.castka.replace(',', '.'),
                kategorie_id: manualForm.kategorie_id || null,
                prodejna_id: manualForm.prodejna_id || null,
            });
            setMessage('Ruční náklad uložen.');
            setManualForm((f) => ({ ...f, castka: '', popis: '', poznamka_admin: '' }));
            loadAll();
        } catch (err) {
            setMessage(err.response?.data?.error || 'Uložení selhalo');
        }
    };

    const handleCategorize = async (polozka) => {
        const kategorieId = document.getElementById(`kat-${polozka.id}`)?.value;
        if (!kategorieId) {
            setMessage('Vyberte kategorii.');
            return;
        }
        try {
            await financeAPI.updateNaklad(polozka.id, {
                kategorie_id: Number(kategorieId),
                zaradit: true,
                poznamka_admin: document.getElementById(`note-${polozka.id}`)?.value || '',
            });
            setMessage(`Položka #${polozka.id} zařazena.`);
            loadAll();
        } catch (err) {
            setMessage(err.response?.data?.error || 'Zařazení selhalo');
        }
    };

    const fioNote = status?.fio?.message || 'Fio token vyžaduje admin účet – zatím nedostupné';

    return (
        <div className="finance-module">
            <PageHeader title="Finance" subtitle="Admin sekce – náklady a Fio" />

            <div className="finance-fio-banner" role="status">
                <strong>Fio banka:</strong> {fioNote}
                <span className="finance-fio-banner__hint">
                    Ruční náklady jsou aktivní. Packeta import je v Analytika → Zásilkovna.
                </span>
            </div>

            <nav className="finance-tabs" aria-label="Finance záložky">
                <button
                    type="button"
                    className={tab === 'k-zarazeni' ? 'active' : ''}
                    onClick={() => setTab('k-zarazeni')}
                >
                    K zařazení
                </button>
                <button
                    type="button"
                    className={tab === 'manual' ? 'active' : ''}
                    onClick={() => setTab('manual')}
                >
                    Ruční náklad
                </button>
            </nav>

            {loading && <p className="finance-loading">Načítám…</p>}
            {error && <p className="finance-error">{error}</p>}
            {message && <p className="finance-message">{message}</p>}

            {!loading && tab === 'k-zarazeni' && (
                <section className="finance-panel">
                    <p className="finance-panel__intro">
                        Fronta nezařazených pohybů (typicky z Fio). Dokud není aktivní Fio import,
                        seznam bude prázdný – použijte záložku Ruční náklad.
                    </p>
                    {nezarazene.length === 0 ? (
                        <p className="finance-empty">Žádné nezařazené položky.</p>
                    ) : (
                        <div className="finance-table-wrap">
                            <table className="finance-table">
                                <thead>
                                    <tr>
                                        <th>Datum</th>
                                        <th>Částka</th>
                                        <th>Protiúčet</th>
                                        <th>Zpráva</th>
                                        <th>Kategorie</th>
                                        <th>Akce</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {nezarazene.map((p) => (
                                        <tr key={p.id}>
                                            <td>{p.datum}</td>
                                            <td>{formatCurrency(p.castka)}</td>
                                            <td>{p.protiucet || '–'}</td>
                                            <td className="finance-cell-zprava">{p.zprava || p.popis || '–'}</td>
                                            <td>
                                                <select id={`kat-${p.id}`} defaultValue="">
                                                    <option value="">— vyberte —</option>
                                                    {kategorie.map((k) => (
                                                        <option key={k.id} value={k.id}>{k.nazev}</option>
                                                    ))}
                                                </select>
                                            </td>
                                            <td>
                                                <input
                                                    id={`note-${p.id}`}
                                                    type="text"
                                                    placeholder="Poznámka"
                                                    className="finance-note-input"
                                                />
                                                <button type="button" onClick={() => handleCategorize(p)}>
                                                    Zařadit
                                                </button>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </section>
            )}

            {!loading && tab === 'manual' && (
                <section className="finance-panel">
                    <form className="finance-form" onSubmit={handleManualSubmit}>
                        <label>
                            Datum
                            <input
                                type="date"
                                value={manualForm.datum}
                                onChange={(e) => setManualForm((f) => ({ ...f, datum: e.target.value }))}
                                required
                            />
                        </label>
                        <label>
                            Částka (Kč, záporná = výdaj)
                            <input
                                type="text"
                                value={manualForm.castka}
                                onChange={(e) => setManualForm((f) => ({ ...f, castka: e.target.value }))}
                                placeholder="-1500"
                                required
                            />
                        </label>
                        <label>
                            Kategorie
                            <select
                                value={manualForm.kategorie_id}
                                onChange={(e) => setManualForm((f) => ({ ...f, kategorie_id: e.target.value }))}
                            >
                                <option value="">— bez kategorie —</option>
                                {kategorie.map((k) => (
                                    <option key={k.id} value={k.id}>{k.nazev}</option>
                                ))}
                            </select>
                        </label>
                        <label>
                            Prodejna
                            <select
                                value={manualForm.prodejna_id}
                                onChange={(e) => setManualForm((f) => ({ ...f, prodejna_id: e.target.value }))}
                            >
                                <option value="">— firma / bez prodejny —</option>
                                {stores.map((s) => (
                                    <option key={s.id} value={s.id}>{s.nazev || s.label}</option>
                                ))}
                            </select>
                        </label>
                        <label>
                            Popis
                            <input
                                type="text"
                                value={manualForm.popis}
                                onChange={(e) => setManualForm((f) => ({ ...f, popis: e.target.value }))}
                            />
                        </label>
                        <button type="submit" className="finance-btn-primary">Uložit náklad</button>
                    </form>
                </section>
            )}
        </div>
    );
};

export default FinanceModule;
