import React, { useCallback, useEffect, useState } from 'react';
import { PageHeader } from '../../components/ui';
import { financeAPI, storeAPI } from '../../services/api';
import './FinanceModule.css';
import FinanceFakturyPanel from './FinanceFakturyPanel';
import FinancePrehledPanel from './FinancePrehledPanel';
import FinanceKontrolaPanel from './FinanceKontrolaPanel';
import FinanceDokladUpload from './FinanceDokladUpload';
import FinanceZdrojFilter from './FinanceZdrojFilter';
import { kategorieProZarazeni, movementLabel, parseStoreChoices, storeLabel, zdrojMeta } from './financeUtils';

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
    const [jenBezFaktury, setJenBezFaktury] = useState(false);
    const [filterZdroj, setFilterZdroj] = useState('');
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

    const [katForm, setKatForm] = useState({
        nazev: '',
        parent_id: '',
        typ_dph: 'z_faktury',
        poradi: '0',
    });

    const loadAll = useCallback(async () => {
        setLoading(true);
        setError('');
        try {
            const [st, kat, nz, storeChoices, rules] = await Promise.all([
                financeAPI.getStatus(),
                financeAPI.getKategorie(),
                financeAPI.getNezarazene(jenBezFaktury ? { bez_faktury: '1' } : {}),
                storeAPI.getStoreChoices(),
                financeAPI.getPravidla(),
            ]);
            setStatus(st);
            setKategorie(Array.isArray(kat) ? kat : []);
            setNezarazene(Array.isArray(nz) ? nz : []);
            setPravidla(Array.isArray(rules) ? rules : []);
            setStores(parseStoreChoices(storeChoices));
        } catch (e) {
            setError(e.response?.data?.error || e.message || 'Chyba načítání');
        } finally {
            setLoading(false);
        }
    }, [jenBezFaktury]);

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
        const resolvedProdejna = prodejnaId
            ? Number(prodejnaId)
            : (polozka.prodejna_id ? Number(polozka.prodejna_id) : null);
        try {
            const res = await financeAPI.updateNaklad(polozka.id, {
                kategorie_id: Number(kategorieId),
                prodejna_id: resolvedProdejna,
                zaradit: true,
                poznamka_admin: document.getElementById(`note-${polozka.id}`)?.value || '',
            });
            let msg = `Položka #${polozka.id} zařazena.`;
            if (res?.pravidlo_created || res?.pravidlo_updated) {
                msg += ' Pravidlo uloženo pro další podobné náklady.';
            }
            setMessage(msg);
            loadAll();
        } catch (err) {
            setMessage(err.response?.data?.error || 'Zařazení selhalo');
        }
    };

    const handleKategorieSubmit = async (e) => {
        e.preventDefault();
        setMessage('');
        try {
            await financeAPI.createKategorie({
                nazev: katForm.nazev.trim(),
                parent_id: katForm.parent_id || null,
                typ_dph: katForm.typ_dph,
                poradi: Number(katForm.poradi) || 0,
            });
            setMessage('Kategorie vytvořena.');
            setKatForm({ nazev: '', parent_id: '', typ_dph: 'z_faktury', poradi: '0' });
            loadAll();
        } catch (err) {
            setMessage(err.response?.data?.error || 'Vytvoření kategorie selhalo');
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

    const kategorieVyber = kategorieProZarazeni(kategorie);
    const zobrazeno = filterZdroj
        ? nezarazene.filter((p) => p.zdroj === filterZdroj)
        : nezarazene;

    return (
        <div className="finance-module">
            <PageHeader title="Finance" subtitle="Admin sekce – náklady a Fio" />

            <div className="finance-status-panel" role="status">
                <div className="finance-status-panel__row">
                    <span><strong>Chybí zařazení:</strong> {counts.nezarazene ?? '–'}</span>
                    <span><strong>Auto zařazeno:</strong> {counts.auto_zarazeno ?? '–'}</span>
                    <span><strong>Ručně:</strong> {counts.rucne_zarazeno ?? '–'}</span>
                    <span><strong>Ignorovat:</strong> {counts.ignorovano ?? '–'}</span>
                </div>
                <div className="finance-status-panel__row">
                    <span><strong>Čeká na fakturu:</strong> {counts.ceka_na_fakturu ?? '–'}</span>
                    <span><strong>Bez faktury (DPH):</strong> {counts.bez_faktury ?? '–'}</span>
                    <span><strong>Ke kontrole FA:</strong> {counts.doklady_ke_kontrole ?? '–'}</span>
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
                    className={tab === 'prehled' ? 'active' : ''}
                    onClick={() => setTab('prehled')}
                >
                    Přehled
                </button>
                <button
                    type="button"
                    className={tab === 'kontrola' ? 'active' : ''}
                    onClick={() => setTab('kontrola')}
                >
                    Kontrola FA
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
                <button
                    type="button"
                    className={tab === 'kategorie' ? 'active' : ''}
                    onClick={() => setTab('kategorie')}
                >
                    Kategorie
                </button>
            </nav>

            {loading && <p className="finance-loading">Načítám…</p>}
            {error && <p className="finance-error">{error}</p>}
            {message && <p className="finance-message">{message}</p>}

            {!loading && tab === 'k-zarazeni' && (
                <section className="finance-panel">
                    <p className="finance-panel__intro">
                        Fronta odchozích plateb (Fio / pokladna). U výdejů z kasy je prodejna
                        doplněná z pokladny. Zařazení = kategorie + prodejna (u Reklamy/Nájmu stačí
                        obecná kategorie a prodejna zvlášť).
                    </p>
                    <label className="finance-checkbox-label finance-filter-row">
                        <input
                            type="checkbox"
                            checked={jenBezFaktury}
                            onChange={(e) => setJenBezFaktury(e.target.checked)}
                        />
                        Jen bez faktury (včetně už zařazených)
                    </label>
                    <FinanceZdrojFilter
                        value={filterZdroj}
                        onChange={setFilterZdroj}
                        items={nezarazene}
                    />
                    {zobrazeno.length === 0 ? (
                        <p className="finance-empty">Žádné položky pro zvolený filtr.</p>
                    ) : (
                        <div className="finance-table-wrap">
                            <table className="finance-table">
                                <thead>
                                    <tr>
                                        <th>Datum</th>
                                        <th>Účet</th>
                                        <th>Částka</th>
                                        <th>DPH</th>
                                        <th>Protiúčet</th>
                                        <th>Popis</th>
                                        <th>Kategorie</th>
                                        <th>Prodejna</th>
                                        <th>FA</th>
                                        <th>Akce</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {zobrazeno.map((p) => {
                                        const src = zdrojMeta(p.zdroj);
                                        return (
                                        <tr key={p.id} className={src.rowClass}>
                                            <td>{p.datum}</td>
                                            <td>
                                                <span className={`finance-badge ${src.badgeClass}`} title={src.label}>
                                                    {src.short}
                                                </span>
                                            </td>
                                            <td className="finance-cell-castka">{formatCurrency(p.castka)}</td>
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
                                            <td className="finance-cell-zprava">{movementLabel(p)}</td>
                                            <td>
                                                <select
                                                    id={`kat-${p.id}`}
                                                    defaultValue={p.kategorie_id || ''}
                                                >
                                                    <option value="">— vyberte —</option>
                                                    {kategorieVyber.map((k) => (
                                                        <option key={k.id} value={k.id}>{k.nazev}</option>
                                                    ))}
                                                </select>
                                            </td>
                                            <td>
                                                <select
                                                    id={`store-${p.id}`}
                                                    defaultValue={p.prodejna_id ? String(p.prodejna_id) : ''}
                                                >
                                                    <option value="">— firma —</option>
                                                    {stores.map((s) => (
                                                        <option key={s.id} value={s.id}>
                                                            {s.nazev || s.nazev_kratkiy || s.label}
                                                        </option>
                                                    ))}
                                                </select>
                                                {p.prodejna_id && (
                                                    <span className="finance-store-hint" title="Z importu pokladny">
                                                        {p.prodejna_nazev || storeLabel(stores, p.prodejna_id)}
                                                    </span>
                                                )}
                                            </td>
                                            <td>
                                                <FinanceDokladUpload
                                                    polozka={p}
                                                    compact
                                                    onUploaded={loadAll}
                                                />
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
                                        );
                                    })}
                                </tbody>
                            </table>
                        </div>
                    )}
                </section>
            )}

            {tab === 'prehled' && (
                <FinancePrehledPanel
                    kategorie={kategorieVyber}
                    onMessage={setMessage}
                />
            )}

            {!loading && tab === 'kontrola' && <FinanceKontrolaPanel />}

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
                                {kategorieVyber.map((k) => (
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

            {!loading && tab === 'kategorie' && (
                <section className="finance-panel">
                    <p className="finance-panel__intro">
                        Nová kategorie nákladů – po uložení se objeví ve všech výběrech.
                    </p>
                    <form className="finance-form" onSubmit={handleKategorieSubmit}>
                        <label>
                            Název
                            <input
                                type="text"
                                value={katForm.nazev}
                                onChange={(e) => setKatForm((f) => ({ ...f, nazev: e.target.value }))}
                                required
                            />
                        </label>
                        <label>
                            Nadřazená
                            <select
                                value={katForm.parent_id}
                                onChange={(e) => setKatForm((f) => ({ ...f, parent_id: e.target.value }))}
                            >
                                <option value="">— kořenová —</option>
                                {kategorie.filter((k) => !k.parent_id).map((k) => (
                                    <option key={k.id} value={k.id}>{k.nazev}</option>
                                ))}
                            </select>
                        </label>
                        <label>
                            Typ DPH
                            <select
                                value={katForm.typ_dph}
                                onChange={(e) => setKatForm((f) => ({ ...f, typ_dph: e.target.value }))}
                            >
                                <option value="z_faktury">DPH z faktury</option>
                                <option value="bez">Bez DPH</option>
                            </select>
                        </label>
                        <label>
                            Pořadí
                            <input
                                type="number"
                                value={katForm.poradi}
                                onChange={(e) => setKatForm((f) => ({ ...f, poradi: e.target.value }))}
                            />
                        </label>
                        <button type="submit" className="finance-btn-primary">Vytvořit kategorii</button>
                    </form>
                    <div className="finance-table-wrap finance-table-wrap--top">
                        <table className="finance-table">
                            <thead>
                                <tr>
                                    <th>Název</th>
                                    <th>Parent</th>
                                    <th>DPH</th>
                                    <th>Pořadí</th>
                                </tr>
                            </thead>
                            <tbody>
                                {kategorie.map((k) => (
                                    <tr key={k.id}>
                                        <td>{k.nazev}</td>
                                        <td>
                                            {k.parent_id
                                                ? (kategorie.find((x) => x.id === k.parent_id)?.nazev || k.parent_id)
                                                : '–'}
                                        </td>
                                        <td>{k.typ_dph === 'bez' ? 'bez DPH' : 'z faktury'}</td>
                                        <td>{k.poradi}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
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
                                {kategorieVyber.map((k) => (
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
