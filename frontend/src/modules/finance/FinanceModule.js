import React, { useCallback, useEffect, useState } from 'react';
import { PageHeader } from '../../components/ui';
import { financeAPI, storeAPI } from '../../services/api';
import './FinanceModule.css';
import FinanceFakturyPanel from './FinanceFakturyPanel';

const formatCurrency = (value) => {
    const n = Number(value) || 0;
    return new Intl.NumberFormat('cs-CZ', {
        style: 'currency',
        currency: 'CZK',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
    }).format(Math.round(n));
};

const DPH_BADGE_LABELS = {
    ceka_na_fakturu: 'čeká na fakturu',
    sparovano: 'spárováno',
    bez_dph: 'bez DPH',
};

const FinanceModule = () => {
    const [tab, setTab] = useState('k-zarazeni');
    const [status, setStatus] = useState(null);
    const [kategorie, setKategorie] = useState([]);
    const [stores, setStores] = useState([]);
    const [nezarazene, setNezarazene] = useState([]);
    const [pravidla, setPravidla] = useState([]);
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

    const [pravidloForm, setPravidloForm] = useState({
        protiucet: '',
        zprava_obsahuje: '',
        vs: '',
        kategorie_id: '',
        prodejna_id: '',
        ignorovat: false,
    });

    const loadAll = useCallback(async () => {
        setLoading(true);
        setError('');
        try {
            const [st, kat, nz, storeChoices, rules] = await Promise.all([
                financeAPI.getStatus(),
                financeAPI.getKategorie(),
                financeAPI.getNezarazene(),
                storeAPI.getStoreChoices(),
                financeAPI.getPravidla(),
            ]);
            setStatus(st);
            setKategorie(Array.isArray(kat) ? kat : []);
            setNezarazene(Array.isArray(nz) ? nz : []);
            setPravidla(Array.isArray(rules) ? rules : []);
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
        const prodejnaId = document.getElementById(`store-${polozka.id}`)?.value;
        try {
            await financeAPI.updateNaklad(polozka.id, {
                kategorie_id: Number(kategorieId),
                prodejna_id: prodejnaId ? Number(prodejnaId) : null,
                zaradit: true,
                poznamka_admin: document.getElementById(`note-${polozka.id}`)?.value || '',
            });
            setMessage(`Položka #${polozka.id} zařazena.`);
            loadAll();
        } catch (err) {
            setMessage(err.response?.data?.error || 'Zařazení selhalo');
        }
    };

    const handlePravidloSubmit = async (e) => {
        e.preventDefault();
        setMessage('');
        try {
            await financeAPI.createPravidlo({
                ...pravidloForm,
                kategorie_id: pravidloForm.kategorie_id || null,
                prodejna_id: pravidloForm.prodejna_id || null,
            });
            setMessage('Pravidlo uloženo.');
            setPravidloForm({
                protiucet: '',
                zprava_obsahuje: '',
                vs: '',
                kategorie_id: '',
                prodejna_id: '',
                ignorovat: false,
            });
            loadAll();
        } catch (err) {
            setMessage(err.response?.data?.error || 'Uložení pravidla selhalo');
        }
    };

    const handleDeletePravidlo = async (id) => {
        if (!window.confirm('Smazat toto pravidlo?')) return;
        try {
            await financeAPI.deletePravidlo(id);
            setMessage('Pravidlo smazáno.');
            loadAll();
        } catch (err) {
            setMessage(err.response?.data?.error || 'Smazání selhalo');
        }
    };

    const fioNote = status?.fio?.message || 'Fio token vyžaduje admin účet – zatím nedostupné';
    const counts = status?.counts || {};
    const lastImport = status?.fio?.last_import;

    return (
        <div className="finance-module">
            <PageHeader title="Finance" subtitle="Admin sekce – náklady a Fio" />

            <div className="finance-status-panel" role="status">
                <div className="finance-status-panel__row">
                    <span><strong>Nezařazené:</strong> {counts.nezarazene ?? '–'}</span>
                    <span><strong>Čeká na fakturu:</strong> {counts.ceka_na_fakturu ?? '–'}</span>
                    <span>
                        <strong>Poslední Fio import:</strong>{' '}
                        {lastImport?.vytvoreno
                            ? new Date(lastImport.vytvoreno).toLocaleString('cs-CZ')
                            : 'zatím žádný'}
                    </span>
                </div>
            </div>

            <div className="finance-fio-banner" role="status">
                <strong>Fio banka:</strong> {fioNote}
                <span className="finance-fio-banner__hint">
                    DPH se doplní až po nahrání faktury (OCR). Import běží cronem ve 22:30.
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
                    className={tab === 'faktury' ? 'active' : ''}
                    onClick={() => setTab('faktury')}
                >
                    Faktury
                </button>
                <button
                    type="button"
                    className={tab === 'manual' ? 'active' : ''}
                    onClick={() => setTab('manual')}
                >
                    Ruční náklad
                </button>
                <button
                    type="button"
                    className={tab === 'pravidla' ? 'active' : ''}
                    onClick={() => setTab('pravidla')}
                >
                    Pravidla
                </button>
            </nav>

            {loading && <p className="finance-loading">Načítám…</p>}
            {error && <p className="finance-error">{error}</p>}
            {message && <p className="finance-message">{message}</p>}

            {!loading && tab === 'k-zarazeni' && (
                <section className="finance-panel">
                    <p className="finance-panel__intro">
                        Fronta nezařazených odchozích plateb (Fio / pokladna). Zařazení = kategorie + prodejna,
                        bez ručního DPH.
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
                                        <th>DPH</th>
                                        <th>Protiúčet</th>
                                        <th>Zpráva</th>
                                        <th>Kategorie</th>
                                        <th>Prodejna</th>
                                        <th>Akce</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {nezarazene.map((p) => (
                                        <tr key={p.id}>
                                            <td>{p.datum}</td>
                                            <td>{formatCurrency(p.castka)}</td>
                                            <td>
                                                {p.dph_stav === 'ceka_na_fakturu' ? (
                                                    <span className="finance-badge finance-badge--warn">
                                                        {DPH_BADGE_LABELS.ceka_na_fakturu}
                                                    </span>
                                                ) : (
                                                    <span className="finance-badge">
                                                        {DPH_BADGE_LABELS[p.dph_stav] || p.dph_stav}
                                                    </span>
                                                )}
                                            </td>
                                            <td>{p.protiucet || '–'}</td>
                                            <td className="finance-cell-zprava">
                                                {p.zdroj === 'symplio_pokladna' && (
                                                    <span className="finance-badge" title="Symplio pokladna">kasa</span>
                                                )}
                                                {p.zdroj === 'fio' && (
                                                    <span className="finance-badge" title="Fio banka">fio</span>
                                                )}
                                                {' '}
                                                {p.zdroj === 'symplio_pokladna'
                                                    ? (p.popis || p.zprava || '–')
                                                    : (p.zprava || p.popis || '–')}
                                            </td>
                                            <td>
                                                <select id={`kat-${p.id}`} defaultValue="">
                                                    <option value="">— vyberte —</option>
                                                    {kategorie.map((k) => (
                                                        <option key={k.id} value={k.id}>{k.nazev}</option>
                                                    ))}
                                                </select>
                                            </td>
                                            <td>
                                                <select id={`store-${p.id}`} defaultValue="">
                                                    <option value="">— firma —</option>
                                                    {stores.map((s) => (
                                                        <option key={s.id} value={s.id}>{s.nazev || s.label}</option>
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

            {!loading && tab === 'faktury' && (
                <FinanceFakturyPanel intro="Výdaje čekající na fakturu – admin vidí všechny prodejny." />
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

            {!loading && tab === 'pravidla' && (
                <section className="finance-panel">
                    <p className="finance-panel__intro">
                        Automatické zařazení Fio plateb podle protistrany, VS nebo textu zprávy.
                    </p>
                    <form className="finance-form finance-form--wide" onSubmit={handlePravidloSubmit}>
                        <label>
                            Protiúčet (obsahuje)
                            <input
                                type="text"
                                value={pravidloForm.protiucet}
                                onChange={(e) => setPravidloForm((f) => ({ ...f, protiucet: e.target.value }))}
                            />
                        </label>
                        <label>
                            Zpráva obsahuje
                            <input
                                type="text"
                                value={pravidloForm.zprava_obsahuje}
                                onChange={(e) => setPravidloForm((f) => ({ ...f, zprava_obsahuje: e.target.value }))}
                            />
                        </label>
                        <label>
                            VS
                            <input
                                type="text"
                                value={pravidloForm.vs}
                                onChange={(e) => setPravidloForm((f) => ({ ...f, vs: e.target.value }))}
                            />
                        </label>
                        <label>
                            Kategorie
                            <select
                                value={pravidloForm.kategorie_id}
                                onChange={(e) => setPravidloForm((f) => ({ ...f, kategorie_id: e.target.value }))}
                            >
                                <option value="">— ignorovat / bez —</option>
                                {kategorie.map((k) => (
                                    <option key={k.id} value={k.id}>{k.nazev}</option>
                                ))}
                            </select>
                        </label>
                        <label>
                            Prodejna
                            <select
                                value={pravidloForm.prodejna_id}
                                onChange={(e) => setPravidloForm((f) => ({ ...f, prodejna_id: e.target.value }))}
                            >
                                <option value="">— bez —</option>
                                {stores.map((s) => (
                                    <option key={s.id} value={s.id}>{s.nazev || s.label}</option>
                                ))}
                            </select>
                        </label>
                        <label className="finance-checkbox-label">
                            <input
                                type="checkbox"
                                checked={pravidloForm.ignorovat}
                                onChange={(e) => setPravidloForm((f) => ({ ...f, ignorovat: e.target.checked }))}
                            />
                            Ignorovat (interní převod)
                        </label>
                        <button type="submit" className="finance-btn-primary">Přidat pravidlo</button>
                    </form>

                    {pravidla.length === 0 ? (
                        <p className="finance-empty">Žádná pravidla.</p>
                    ) : (
                        <div className="finance-table-wrap finance-table-wrap--top">
                            <table className="finance-table">
                                <thead>
                                    <tr>
                                        <th>Protiúčet</th>
                                        <th>Zpráva</th>
                                        <th>VS</th>
                                        <th>Kategorie</th>
                                        <th>Ignorovat</th>
                                        <th></th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {pravidla.map((r) => (
                                        <tr key={r.id}>
                                            <td>{r.protiucet || '–'}</td>
                                            <td>{r.zprava_obsahuje || '–'}</td>
                                            <td>{r.vs || '–'}</td>
                                            <td>{r.kategorie_nazev || '–'}</td>
                                            <td>{r.ignorovat ? 'ano' : 'ne'}</td>
                                            <td>
                                                <button type="button" onClick={() => handleDeletePravidlo(r.id)}>
                                                    Smazat
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
        </div>
    );
};

export default FinanceModule;
