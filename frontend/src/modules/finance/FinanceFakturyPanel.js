import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { financeAPI } from '../../services/api';
import FinanceZdrojFilter from './FinanceZdrojFilter';
import FinanceDropZone from './FinanceDropZone';
import FinanceDokladSummary from './FinanceDokladSummary';
import FinanceDokladEditForm from './FinanceDokladEditForm';
import { movementLabel, zdrojMeta } from './financeUtils';
import './FinanceFakturyPanel.css';

const sameStore = (a, b) => a != null && b != null && String(a) === String(b);

const formatCurrency = (value) => {
    const n = Number(value) || 0;
    return new Intl.NumberFormat('cs-CZ', {
        style: 'currency',
        currency: 'CZK',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
    }).format(Math.round(n));
};

const stavLabel = (stav) => {
    if (stav === 'zamitnuto') return 'Zamítnuto – upravte a uložte znovu';
    if (stav === 'ceka_na_ocr') return 'Čeká na vyčtení';
    return 'Čeká na schválení';
};

const FinanceFakturyPanel = ({ intro }) => {
    const [items, setItems] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [message, setMessage] = useState('');
    const [uploadingId, setUploadingId] = useState(null);
    const [savingId, setSavingId] = useState(null);
    const [replacingId, setReplacingId] = useState(null);
    const [forms, setForms] = useState({});
    const [filterZdroj, setFilterZdroj] = useState('');
    /** undefined = server zvolí výchozí prodejnu; číslo nebo 'all' = ruční volba. */
    const [prodejnaParam, setProdejnaParam] = useState(undefined);
    const [prodejny, setProdejny] = useState(null);
    const [vybrana, setVybrana] = useState('all');
    const [pocetVse, setPocetVse] = useState(0);
    /** Nahrané faktury k opravě, dokud je neschválí admin. */
    const [nahrane, setNahrane] = useState([]);

    const load = useCallback(async () => {
        setLoading(true);
        setError('');
        try {
            const params = {};
            if (prodejnaParam !== undefined) params.prodejna_id = prodejnaParam;
            const [data, uploaded] = await Promise.all([
                financeAPI.getCekaNaFakturu(params),
                financeAPI.getDoklady(),
            ]);
            if (Array.isArray(data)) {
                setItems(data);
                setProdejny(null);
                setVybrana('all');
                setPocetVse(data.length);
            } else {
                const rows = Array.isArray(data?.items) ? data.items : [];
                setItems(rows);
                setProdejny(Array.isArray(data?.prodejny) ? data.prodejny : null);
                setVybrana(data?.prodejna_id ?? 'all');
                setPocetVse(data?.pocet_vse ?? rows.length);
            }
            setNahrane(Array.isArray(uploaded) ? uploaded : []);
        } catch (e) {
            setError(e.response?.data?.error || e.message || 'Chyba načítání');
        } finally {
            setLoading(false);
        }
    }, [prodejnaParam]);

    useEffect(() => {
        load();
    }, [load]);

    const waiting = useMemo(
        () => (filterZdroj ? items.filter((p) => p.zdroj === filterZdroj) : items),
        [items, filterZdroj],
    );

    const nahraneFiltered = useMemo(() => {
        let rows = nahrane;
        if (vybrana !== 'all') {
            rows = rows.filter((d) => sameStore(d.naklad_polozka?.prodejna_id, vybrana));
        }
        if (filterZdroj) {
            rows = rows.filter((d) => (d.naklad_polozka?.zdroj || '') === filterZdroj);
        }
        return rows;
    }, [nahrane, filterZdroj, vybrana]);

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
            await financeAPI.uploadDoklad({
                file,
                naklad_polozka_id: polozka.id,
                cislo_faktury: form.cislo_faktury || '',
                dodavatel_nazev: form.dodavatel_nazev || '',
                castka_bez_dph: form.castka_bez_dph || '',
                dph_castka: form.dph_castka || '',
                dph_sazba: form.dph_sazba || '',
            });
            setMessage('Faktura uložena. Údaje můžete opravit, dokud ji neschválí admin.');
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

    const saveDoklad = async (id, payload) => {
        setSavingId(id);
        setMessage('');
        try {
            await financeAPI.updateDoklad(id, payload);
            setMessage('Údaje faktury uloženy.');
            load();
        } catch (e) {
            setMessage(e.response?.data?.error || 'Uložení selhalo');
        } finally {
            setSavingId(null);
        }
    };

    const replaceSoubor = async (id, file) => {
        if (!file) return;
        setReplacingId(id);
        setMessage('');
        try {
            await financeAPI.replaceDokladSoubor(id, file);
            setMessage('Soubor faktury nahrazen.');
            load();
        } catch (e) {
            setMessage(e.response?.data?.error || 'Nahrazení souboru selhalo');
        } finally {
            setReplacingId(null);
        }
    };

    const renderUploaded = (d) => {
        const p = d.naklad_polozka || {};
        const src = zdrojMeta(p.zdroj, p.pokladna_label);
        const editable = d.lze_upravit !== false;
        const duvod = d.match_detail?.zamitnuto_duvod;
        return (
            <article key={d.id} className="finance-faktury-card finance-faktury-card--done">
                <div className="finance-faktury-card__head">
                    <span className={`finance-badge ${d.stav === 'zamitnuto' ? 'finance-badge--warn' : 'finance-badge--ok'}`}>
                        {stavLabel(d.stav)}
                    </span>
                    {p.zdroj && <span className={`finance-badge ${src.badgeClass}`}>{src.label}</span>}
                    {p.datum && <span>{p.datum}</span>}
                    {p.castka != null && <strong>{formatCurrency(p.castka)}</strong>}
                </div>
                <p className="finance-faktury-card__text">
                    {p.id ? movementLabel(p) : 'Faktura bez vazby na výdej'}
                </p>
                {d.stav === 'zamitnuto' && duvod && (
                    <p className="finance-faktury-card__parsed finance-faktury-card__parsed--warn">{duvod}</p>
                )}
                <FinanceDokladSummary doklad={d} />
                {editable && (
                    <>
                        <FinanceDokladEditForm
                            key={`${d.id}-${d.upraveno || d.vytvoreno || ''}`}
                            doklad={d}
                            busy={savingId === d.id || replacingId === d.id}
                            onSave={(payload) => saveDoklad(d.id, payload)}
                        />
                        <div className="finance-faktury-replace">
                            <FinanceDropZone
                                compact
                                disabled={replacingId === d.id || savingId === d.id}
                                label={replacingId === d.id ? 'Nahrávám…' : 'Nahradit soubor (PDF / foto)'}
                                onFile={(file) => replaceSoubor(d.id, file)}
                            />
                        </div>
                    </>
                )}
            </article>
        );
    };

    const renderCard = (p) => {
        const src = zdrojMeta(p.zdroj, p.pokladna_label);
        const form = formFor(p);
        return (
            <article
                key={p.id}
                className={`finance-faktury-card ${src.rowClass}`}
            >
                <div className="finance-faktury-card__head">
                    <span className={`finance-badge ${src.badgeClass}`}>{src.label}</span>
                    <span>{p.datum}</span>
                    <strong>{formatCurrency(p.castka)}</strong>
                </div>
                <p className="finance-faktury-card__text">{movementLabel(p)}</p>
                {p.faktura_hint && (
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
            </article>
        );
    };

    const empty = !loading && waiting.length === 0 && nahraneFiltered.length === 0;
    const jinde = Array.isArray(prodejny)
        ? prodejny.filter((store) => !sameStore(store.id, vybrana) && (store.pocet || 0) > 0)
        : [];

    return (
        <section className="finance-faktury-panel">
            {intro && <p className="finance-faktury-panel__intro">{intro}</p>}
            <p className="finance-faktury-panel__hint">
                Výdej z pokladny se sem dostane během dne (import ze Symplio cca každých
                30&nbsp;min mezi 8:30–21:00). Prodejna je podle pokladny, kde byl výběr.
            </p>
            {Array.isArray(prodejny) && prodejny.length > 1 && (
                <div className="finance-faktury-stores" role="group" aria-label="Prodejna">
                    {prodejny.map((store) => {
                        const active = sameStore(vybrana, store.id);
                        const tags = [
                            store.je_domaci ? 'domácí' : '',
                            store.je_aktualni_smena && !store.je_domaci ? 'směna' : '',
                        ].filter(Boolean);
                        return (
                            <button
                                key={store.id}
                                type="button"
                                className={`finance-filter-chip${active ? ' active' : ''}`}
                                onClick={() => setProdejnaParam(store.id)}
                            >
                                {store.nazev}
                                {tags.length > 0 && (
                                    <span className="finance-faktury-store-tag">{tags.join(', ')}</span>
                                )}
                                <span className="finance-filter-chip__count">{store.pocet ?? 0}</span>
                            </button>
                        );
                    })}
                    <button
                        type="button"
                        className={`finance-filter-chip${vybrana === 'all' ? ' active' : ''}`}
                        onClick={() => setProdejnaParam('all')}
                    >
                        Všechny chybějící
                        <span className="finance-filter-chip__count">{pocetVse}</span>
                    </button>
                </div>
            )}
            {loading && <p>Načítám…</p>}
            {error && <p className="finance-faktury-error">{error}</p>}
            {message && <p className="finance-faktury-message">{message}</p>}
            {!loading && prodejny == null && (items.length > 0 || nahrane.length > 0) && (
                <FinanceZdrojFilter
                    value={filterZdroj}
                    onChange={setFilterZdroj}
                    items={[
                        ...items,
                        ...nahrane.map((d) => d.naklad_polozka).filter(Boolean),
                    ]}
                />
            )}
            {empty && (
                <p className="finance-faktury-empty">
                    {vybrana === 'all' || !Array.isArray(prodejny)
                        ? 'Žádné výdaje nečekají na fakturu.'
                        : 'Na této prodejně nic nečeká na fakturu.'}
                    {vybrana !== 'all' && jinde.length > 0 && (
                        <> Chybějící faktury jsou na {jinde.map((store) => store.nazev).join(', ')}.</>
                    )}
                </p>
            )}
            {!loading && nahraneFiltered.length > 0 && (
                <div className="finance-faktury-list">
                    <h3 className="finance-faktury-section-title">Nahrané faktury</h3>
                    <p className="finance-faktury-panel__hint">
                        Údaje i soubor můžete opravit, dokud fakturu neschválí admin.
                    </p>
                    {nahraneFiltered.map((d) => renderUploaded(d))}
                </div>
            )}
            {!loading && waiting.length > 0 && (
                <div className="finance-faktury-list">
                    {nahraneFiltered.length > 0 && (
                        <h3 className="finance-faktury-section-title">Čeká na fakturu</h3>
                    )}
                    {waiting.map((p) => renderCard(p))}
                </div>
            )}
        </section>
    );
};

export default FinanceFakturyPanel;
