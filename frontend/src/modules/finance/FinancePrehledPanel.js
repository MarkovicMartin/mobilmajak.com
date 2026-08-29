import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { financeAPI } from '../../services/api';
import FinanceZdrojFilter from './FinanceZdrojFilter';
import FinancePravidloDialog from './FinancePravidloDialog';
import { movementLabel, zdrojMeta } from './financeUtils';

const formatCurrency = (value) => {
    const n = Number(value) || 0;
    return new Intl.NumberFormat('cs-CZ', {
        style: 'currency',
        currency: 'CZK',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
    }).format(Math.round(n));
};

const STAV_FILTERS = [
    { id: 'vse', label: 'Vše' },
    { id: 'nezarazeno', label: 'Chybí zařazení' },
    { id: 'auto', label: 'Auto ✓' },
    { id: 'rucne', label: 'Ručně' },
    { id: 'ignorovat', label: 'Ignorovat' },
];

const stavBadge = (p) => {
    if (p.stav === 'ignorovat') return { cls: 'finance-badge--muted', text: 'ignorovat' };
    if (p.stav === 'nezarazeno') return { cls: 'finance-badge--warn', text: 'chybí' };
    if (p.zarazeno_automaticky) {
        return { cls: 'finance-badge--ok', text: p.auto_pravidlo || 'auto' };
    }
    if (p.stav === 'rucne') return { cls: 'finance-badge--manual', text: 'ručně' };
    return { cls: '', text: p.stav };
};

const FinancePrehledPanel = ({ kategorie = [], stores = [], onMessage }) => {
    const [items, setItems] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [stavFilter, setStavFilter] = useState('vse');
    const [filterZdroj, setFilterZdroj] = useState('');
    const [draftKat, setDraftKat] = useState({});
    const [savingId, setSavingId] = useState(null);
    const [pravidloDialog, setPravidloDialog] = useState(null);

    const load = useCallback(async () => {
        setLoading(true);
        setError('');
        try {
            const rows = await financeAPI.getPrehled({
                stav: stavFilter,
                ...(filterZdroj ? { zdroj: filterZdroj } : {}),
            });
            setItems(Array.isArray(rows) ? rows : []);
            setDraftKat({});
        } catch (e) {
            setError(e.response?.data?.error || e.message || 'Chyba načítání');
        } finally {
            setLoading(false);
        }
    }, [stavFilter, filterZdroj]);

    useEffect(() => {
        load();
    }, [load]);

    const counts = useMemo(() => ({
        all: items.length,
        fio: items.filter((p) => p.zdroj === 'fio').length,
        kasa: items.filter((p) => p.zdroj === 'symplio_pokladna').length,
    }), [items]);

    const handleSaveKategorie = async (polozka) => {
        const selected = draftKat[polozka.id];
        const nextId = selected === undefined
            ? (polozka.kategorie_id || '')
            : selected;
        if (!nextId) {
            onMessage?.('Vyberte kategorii.');
            return;
        }
        if (Number(nextId) === Number(polozka.kategorie_id)) {
            onMessage?.('Kategorie beze změny.');
            return;
        }
        setSavingId(polozka.id);
        try {
            const res = await financeAPI.updateNaklad(polozka.id, {
                kategorie_id: Number(nextId),
                zaradit: true,
            });
            onMessage?.(`Kategorie u #${polozka.id} uložena.`);
            setPravidloDialog({
                mode: 'zaradit',
                polozka: { ...polozka, kategorie_id: Number(nextId) },
                navrh: res?.pravidlo_navrh,
            });
            await load();
        } catch (err) {
            onMessage?.(err.response?.data?.error || 'Uložení kategorie selhalo');
        } finally {
            setSavingId(null);
        }
    };

    const handleUnignore = async (polozka) => {
        setSavingId(polozka.id);
        try {
            await financeAPI.updateNaklad(polozka.id, { ignorovat: false });
            onMessage?.(`Ignorování u #${polozka.id} zrušeno.`);
            await load();
        } catch (err) {
            onMessage?.(err.response?.data?.error || 'Změna selhala');
        } finally {
            setSavingId(null);
        }
    };

    return (
        <section className="finance-panel">
            <p className="finance-panel__intro">
                Přehled zařazení: <strong>Auto ✓</strong> = pravidlo + kategorie,
                <strong> chybí</strong> = bez kategorie, <strong>ignorovat</strong> = převody / vklad na účet.
                Kategorii lze změnit i zpětně. Ignorovaná platba se do nákladů nepočítá.
            </p>
            <div className="finance-filters" role="group" aria-label="Filtr stavu">
                {STAV_FILTERS.map((f) => (
                    <button
                        key={f.id}
                        type="button"
                        className={`finance-filter-chip${stavFilter === f.id ? ' active' : ''}`}
                        onClick={() => setStavFilter(f.id)}
                    >
                        {f.label}
                    </button>
                ))}
            </div>
            <FinanceZdrojFilter
                value={filterZdroj}
                onChange={setFilterZdroj}
                items={items}
            />
            {loading && <p>Načítám…</p>}
            {error && <p className="finance-error">{error}</p>}
            {!loading && items.length === 0 && (
                <p className="finance-empty">Žádné položky pro filtr.</p>
            )}
            {!loading && items.length > 0 && (
                <p className="finance-prehled-meta">
                    Zobrazeno {items.length} položek
                    {filterZdroj ? '' : ` (Fio ${counts.fio}, pokladna ${counts.kasa})`}
                </p>
            )}
            {!loading && items.length > 0 && (
                <div className="finance-table-wrap">
                    <table className="finance-table">
                        <thead>
                            <tr>
                                <th>Datum</th>
                                <th>Účet</th>
                                <th>Částka</th>
                                <th>Stav</th>
                                <th>Pravidlo</th>
                                <th>Kategorie</th>
                                <th>Prodejna</th>
                                <th>Popis</th>
                                <th></th>
                            </tr>
                        </thead>
                        <tbody>
                            {items.map((p) => {
                                const src = zdrojMeta(p.zdroj, p.pokladna_label);
                                const badge = stavBadge(p);
                                const current = draftKat[p.id] !== undefined
                                    ? draftKat[p.id]
                                    : (p.kategorie_id ? String(p.kategorie_id) : '');
                                const dirty = draftKat[p.id] !== undefined
                                    && String(draftKat[p.id]) !== String(p.kategorie_id || '');
                                const ignored = p.stav === 'ignorovat' || p.ignorovat;
                                return (
                                    <tr key={p.id} className={src.rowClass}>
                                        <td>{p.datum}</td>
                                        <td>
                                            <span className={`finance-badge ${src.badgeClass}`}>{src.short}</span>
                                            {src.pokladna ? (
                                                <span className="finance-badge finance-badge--pokladna" title={src.label}>
                                                    {src.pokladna}
                                                </span>
                                            ) : null}
                                        </td>
                                        <td>{formatCurrency(p.castka)}</td>
                                        <td>
                                            <span className={`finance-badge ${badge.cls}`}>{badge.text}</span>
                                        </td>
                                        <td className="finance-cell-pravidlo">{p.auto_pravidlo || '–'}</td>
                                        <td>
                                            {kategorie.length > 0 ? (
                                                <div className="finance-kat-edit">
                                                    <select
                                                        value={current}
                                                        onChange={(e) => setDraftKat((d) => ({
                                                            ...d,
                                                            [p.id]: e.target.value,
                                                        }))}
                                                        disabled={savingId === p.id}
                                                    >
                                                        <option value="">— vyberte —</option>
                                                        {kategorie.map((k) => (
                                                            <option key={k.id} value={k.id}>{k.nazev}</option>
                                                        ))}
                                                    </select>
                                                    {dirty && (
                                                        <button
                                                            type="button"
                                                            onClick={() => handleSaveKategorie(p)}
                                                            disabled={savingId === p.id}
                                                        >
                                                            Uložit
                                                        </button>
                                                    )}
                                                </div>
                                            ) : (
                                                p.kategorie_nazev || '–'
                                            )}
                                        </td>
                                        <td>{p.prodejna_nazev || '–'}</td>
                                        <td className="finance-cell-zprava">{movementLabel(p)}</td>
                                        <td>
                                            <div className="finance-row-actions">
                                                {ignored ? (
                                                    <button
                                                        type="button"
                                                        className="finance-btn-secondary"
                                                        disabled={savingId === p.id}
                                                        onClick={() => handleUnignore(p)}
                                                    >
                                                        Zrušit ignorování
                                                    </button>
                                                ) : (
                                                    <button
                                                        type="button"
                                                        className="finance-btn-secondary"
                                                        disabled={savingId === p.id}
                                                        onClick={() => setPravidloDialog({
                                                            mode: 'ignorovat',
                                                            polozka: p,
                                                            keepKatDefault: Boolean(current),
                                                            kategorieId: current || p.kategorie_id,
                                                        })}
                                                    >
                                                        Ignorovat
                                                    </button>
                                                )}
                                            </div>
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            )}
            <FinancePravidloDialog
                open={Boolean(pravidloDialog)}
                mode={pravidloDialog?.mode || 'zaradit'}
                polozka={pravidloDialog?.polozka}
                navrhPayload={pravidloDialog?.navrh}
                kategorie={kategorie}
                stores={stores}
                keepKatDefault={pravidloDialog?.keepKatDefault !== false}
                onSkip={() => {
                    setPravidloDialog(null);
                    load();
                }}
                onConfirmIgnore={async ({ keepKat }) => {
                    const p = pravidloDialog?.polozka;
                    const kid = pravidloDialog?.kategorieId;
                    const payload = {
                        ignorovat: true,
                        zachovat_kategorii: keepKat,
                    };
                    if (keepKat && kid) payload.kategorie_id = Number(kid);
                    const res = await financeAPI.updateNaklad(p.id, payload);
                    onMessage?.(`Položka #${p.id} ignorována.`);
                    await load();
                    return res;
                }}
            />
        </section>
    );
};

export default FinancePrehledPanel;
