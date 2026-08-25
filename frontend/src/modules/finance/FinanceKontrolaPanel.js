import React, { useCallback, useEffect, useState } from 'react';
import { financeAPI } from '../../services/api';
import FinanceDropZone from './FinanceDropZone';
import FinanceDokladEditForm from './FinanceDokladEditForm';
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
    const [uploading, setUploading] = useState(false);

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
            const result = await fn();
            const flexi = result?.flexi;
            if (flexi?.ok && !flexi?.skipped) {
                setMessage(`Uloženo. Flexi FA ${flexi.flexi_kod || flexi.flexi_id} – příloha OK.`);
            } else if (flexi && !flexi.ok && !flexi.skipped) {
                setMessage(`Schváleno lokálně, Flexi: ${flexi.error || 'odeslání selhalo'}`);
            } else {
                setMessage('Uloženo.');
            }
            load();
        } catch (e) {
            setMessage(e.response?.data?.error || 'Akce selhala');
        } finally {
            setBusyId(null);
        }
    };

    const uploadOrphan = async (file) => {
        if (!file) return;
        setUploading(true);
        setMessage('');
        setError('');
        try {
            const result = await financeAPI.uploadDoklad({ file });
            const d = result?.doklad;
            if (d?.prirazeno_automaticky) {
                setMessage(`Nahráno a automaticky přiřazeno (VS ${d.vs || '–'}). Zkontrolujte a schvalte.`);
            } else if (d?.ceka_na_platbu) {
                setMessage(`Nahráno. Čeká na platbu (VS ${d.vs || 'zatím nevyčten'}). Zůstává ke kontrole.`);
            } else {
                setMessage('Nahráno.');
            }
            load();
        } catch (e) {
            setError(e.response?.data?.error || e.message || 'Nahrání selhalo');
        } finally {
            setUploading(false);
        }
    };

    const saveFields = async (id, payload) => {
        setBusyId(id);
        setMessage('');
        try {
            const d = await financeAPI.updateDoklad(id, payload);
            if (d?.prirazeno_automaticky) {
                setMessage(`Údaje uloženy a FA automaticky přiřazena (VS ${d.vs || '–'}).`);
            } else if (d?.ceka_na_platbu) {
                setMessage(`Údaje uloženy (VS ${d.vs || '–'}). Čeká na Fio platbu se stejným VS.`);
            } else {
                setMessage('Údaje uloženy.');
            }
            load();
        } catch (e) {
            setMessage(e.response?.data?.error || 'Uložení selhalo');
        } finally {
            setBusyId(null);
        }
    };

    return (
        <section className="finance-panel finance-kontrola">
            <p className="finance-panel__intro">
                Nahrajte PDF i před platbou – OCR vytáhne VS a částky. Když OCR nic nevyčte, doplňte
                VS ručně. Až přijde Fio se stejným VS, FA se přiřadí automaticky.
            </p>
            <div className="finance-kontrola-upload">
                <FinanceDropZone
                    disabled={uploading}
                    label={uploading ? 'Nahrávám…' : 'Přetáhněte FA sem (i bez platby) nebo klepněte'}
                    onFile={uploadOrphan}
                />
            </div>
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
                                {d.prirazeno_automaticky && (
                                    <span className="finance-match-badge finance-match--auto">Přiřazeno automaticky</span>
                                )}
                                {d.ceka_na_platbu && (
                                    <span className="finance-match-badge finance-match--wait">Čeká na platbu</span>
                                )}
                                <strong>{d.dodavatel_nazev || '–'}</strong>
                                <span>FA {d.cislo_faktury || '–'}</span>
                                <span>VS {d.vs || '–'}</span>
                                {d.soubor_url && (
                                    <a href={d.soubor_url} target="_blank" rel="noopener noreferrer">
                                        Otevřít soubor
                                    </a>
                                )}
                            </header>
                            <div className="finance-kontrola-grid">
                                <div>
                                    <h4>{d.ceka_na_platbu ? 'Platba' : 'Z pokladny / Fio'}</h4>
                                    {d.ceka_na_platbu ? (
                                        <p className="muted">Zatím bez platby – párování podle VS po Fio importu.</p>
                                    ) : hint ? (
                                        <ul>
                                            <li>{hint.dodavatel_nazev}</li>
                                            <li>FA {hint.cislo_faktury}</li>
                                            <li>{formatCurrency(hint.castka_celkem || p?.castka)}</li>
                                            <li className="muted">{p?.popis}</li>
                                        </ul>
                                    ) : (
                                        <ul>
                                            <li>{formatCurrency(p?.castka)}</li>
                                            <li>VS {p?.vs || '–'}</li>
                                            <li className="muted">{p?.popis || 'Fio / ruční'}</li>
                                        </ul>
                                    )}
                                </div>
                                <div>
                                    <FinanceDokladEditForm
                                        doklad={d}
                                        busy={busyId === d.id}
                                        onSave={(payload) => saveFields(d.id, payload)}
                                    />
                                    <p className="muted" style={{ marginTop: '0.35rem' }}>
                                        zdroj OCR: {d.ocr_zdroj || d.ocr_method || '–'}
                                    </p>
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
