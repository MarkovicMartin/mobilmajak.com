import React, { useCallback, useEffect, useState } from 'react';
import { financeAPI } from '../../services/api';
import './FinanceKontrolaPanel.css';

const formatCurrency = (value) => {
    const n = Number(value) || 0;
    return new Intl.NumberFormat('cs-CZ', {
        style: 'currency',
        currency: 'CZK',
        minimumFractionDigits: 0,
        maximumFractionDigits: 2,
    }).format(n);
};

const matchBadge = (stav) => {
    if (stav === 'ok') return { cls: 'finance-match--ok', label: 'Sedí' };
    if (stav === 'fail') return { cls: 'finance-match--fail', label: 'Nesedí' };
    return { cls: 'finance-match--warn', label: 'Kontrola' };
};

const FinanceKontrolaPanel = () => {
    const [items, setItems] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [message, setMessage] = useState('');
    const [busyId, setBusyId] = useState(null);

    const load = useCallback(async () => {
        setLoading(true);
        setError('');
        try {
            const rows = await financeAPI.getDokladyKeKontrole();
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

    const act = async (id, fn) => {
        setBusyId(id);
        setMessage('');
        try {
            await fn();
            setMessage('Uloženo.');
            load();
        } catch (e) {
            setMessage(e.response?.data?.error || 'Akce selhala');
        } finally {
            setBusyId(null);
        }
    };

    return (
        <section className="finance-panel finance-kontrola">
            <p className="finance-panel__intro">
                Faktury po OCR – porovnání s pokladnou. Do Flexi půjdou až po explicitním schválení.
            </p>
            {loading && <p>Načítám…</p>}
            {error && <p className="finance-error">{error}</p>}
            {message && <p className="finance-message">{message}</p>}
            {!loading && items.length === 0 && (
                <p className="finance-empty">Žádné faktury ke kontrole.</p>
            )}
            <div className="finance-kontrola-list">
                {items.map((d) => {
                    const badge = matchBadge(d.match_stav);
                    const p = d.naklad_polozka;
                    const hint = p?.faktura_hint;
                    return (
                        <article key={d.id} className="finance-kontrola-card">
                            <header className="finance-kontrola-card__head">
                                <span className={`finance-match-badge ${badge.cls}`}>{badge.label}</span>
                                <strong>{d.dodavatel_nazev || '–'}</strong>
                                <span>FA {d.cislo_faktury || '–'}</span>
                                {d.soubor_url && (
                                    <a href={d.soubor_url} target="_blank" rel="noopener noreferrer">
                                        Otevřít soubor
                                    </a>
                                )}
                            </header>
                            <div className="finance-kontrola-grid">
                                <div>
                                    <h4>Z pokladny</h4>
                                    {hint ? (
                                        <ul>
                                            <li>{hint.dodavatel_nazev}</li>
                                            <li>FA {hint.cislo_faktury}</li>
                                            <li>{formatCurrency(hint.castka_celkem || p?.castka)}</li>
                                            <li className="muted">{p?.popis}</li>
                                        </ul>
                                    ) : (
                                        <p className="muted">Bez očekávání (Fio / ruční)</p>
                                    )}
                                </div>
                                <div>
                                    <h4>Z faktury (OCR)</h4>
                                    <ul>
                                        <li>{d.dodavatel_nazev || '–'}</li>
                                        <li>FA {d.cislo_faktury || '–'}</li>
                                        <li>
                                            {d.castka_celkem
                                                ? formatCurrency(d.castka_celkem)
                                                : '–'}
                                        </li>
                                        <li>
                                            DPH: {d.castka_bez_dph || '–'} + {d.dph_castka || '–'}
                                            {d.dph_sazba ? ` (${d.dph_sazba} %)` : ''}
                                        </li>
                                        <li className="muted">zdroj: {d.ocr_zdroj || '–'}</li>
                                    </ul>
                                </div>
                            </div>
                            {d.match_detail?.checks?.length > 0 && (
                                <table className="finance-kontrola-checks">
                                    <thead>
                                        <tr>
                                            <th>Pole</th>
                                            <th>Očekáváno</th>
                                            <th>Nalezeno</th>
                                            <th></th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {d.match_detail.checks.map((c) => (
                                            <tr key={c.pole}>
                                                <td>{c.pole}</td>
                                                <td>{c.ocekavano}</td>
                                                <td>{c.nalezeno}</td>
                                                <td>
                                                    <span className={`finance-match-badge finance-match--${c.stav}`}>
                                                        {c.stav}
                                                    </span>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            )}
                            <div className="finance-kontrola-actions">
                                <button
                                    type="button"
                                    disabled={busyId === d.id}
                                    onClick={() => act(d.id, () => financeAPI.schvalitDoklad(d.id))}
                                >
                                    Schválit
                                </button>
                                <button
                                    type="button"
                                    className="secondary"
                                    disabled={busyId === d.id}
                                    onClick={() => act(d.id, () => financeAPI.reprocessDokladOcr(d.id))}
                                >
                                    Znovu OCR
                                </button>
                                <button
                                    type="button"
                                    className="danger"
                                    disabled={busyId === d.id}
                                    onClick={() => {
                                        const duvod = window.prompt('Důvod zamítnutí (volitelné):') || '';
                                        act(d.id, () => financeAPI.zamitnoutDoklad(d.id, { duvod }));
                                    }}
                                >
                                    Zamítnout
                                </button>
                            </div>
                        </article>
                    );
                })}
            </div>
        </section>
    );
};

export default FinanceKontrolaPanel;
