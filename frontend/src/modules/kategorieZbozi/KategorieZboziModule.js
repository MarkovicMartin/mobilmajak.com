import React, { useCallback, useEffect, useState } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import api from '../../services/api';
import Modal from '../../components/Modal';
import { PageHeader, Tabs } from '../../components/ui';
import { useAuth } from '../../context/AuthContext';
import KategorieZboziAudit from './KategorieZboziAudit';
import './KategorieZboziModule.css';

const SYMPLIO_ORDER_URL = (orderId) =>
    `https://www.mobilmajak.cz/admin/objednavky/objednavka-${orderId}`;

const SYMPLIO_KATALOG_URL = (kod) =>
    `https://www.mobilmajak.cz/admin/katalog/vyhledavani?p%5Bhledat%5D=${encodeURIComponent(kod)}`;

const mesicLabel = (rok, mesic) =>
    new Date(rok, mesic - 1, 1).toLocaleDateString('cs-CZ', { month: 'long', year: 'numeric' });

const shiftMonth = (rok, mesic, delta) => {
    const d = new Date(rok, mesic - 1 + delta, 1);
    return { rok: d.getFullYear(), mesic: d.getMonth() + 1 };
};

const jeCizi = (row) => row.claim_stav === 'ceka' && !row.moje;

function ProductTable({ rows, busyKod, onToggle, onOpen }) {
    return (
        <table className="kz-table">
            <thead>
                <tr>
                    <th>Hotovo</th>
                    <th>P kód</th>
                    <th>Název</th>
                    <th>Kategorie</th>
                    <th>Nálezů</th>
                    <th>Ks</th>
                </tr>
            </thead>
            <tbody>
                {rows.map((row) => {
                    const cizi = jeCizi(row);
                    const checked = row.moje || cizi;
                    return (
                        <tr key={row.kod}>
                            <td>
                                <input
                                    type="checkbox"
                                    checked={checked}
                                    disabled={cizi || busyKod === row.kod || row.uz_potvrzeno}
                                    onChange={() => onToggle(row)}
                                    aria-label={`Upraveno v Sympliu ${row.kod}`}
                                />
                            </td>
                            <td>
                                <a
                                    className="kz-link"
                                    href={SYMPLIO_KATALOG_URL(row.kod)}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                >
                                    <code>{row.kod}</code>
                                </a>
                            </td>
                            <td>
                                <button type="button" className="kz-link" onClick={() => onOpen(row)}>
                                    {row.nazev || '—'}
                                </button>
                                {cizi && <div className="kz-note">Čeká na ověření: {row.claim_jmeno}</div>}
                                {row.nepotvrzeno_poznamka && (
                                    <div className="kz-note">{row.nepotvrzeno_poznamka}</div>
                                )}
                            </td>
                            <td>
                                {row.kategorie || '—'}
                                {row.kategorie_1 ? ` · ${row.kategorie_1}` : ''}
                                {row.vice_kategorii ? ' (+ další)' : ''}
                            </td>
                            <td>{row.nalezy}</td>
                            <td>{row.kusy}</td>
                        </tr>
                    );
                })}
            </tbody>
        </table>
    );
}

export default function KategorieZboziModule() {
    const { isAdmin } = useAuth();
    const location = useLocation();
    const audit = location.pathname.endsWith('/audit');
    const today = new Date();
    const [rok, setRok] = useState(today.getFullYear());
    const [mesic, setMesic] = useState(today.getMonth() + 1);
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [busyKod, setBusyKod] = useState('');
    const [detail, setDetail] = useState(null);
    const [detailItems, setDetailItems] = useState([]);
    const [detailLoading, setDetailLoading] = useState(false);

    const load = useCallback(async () => {
        setLoading(true);
        setError('');
        try {
            const res = await api.get('/kategorie-zbozi/', { params: { rok, mesic } });
            setData(res.data);
        } catch (e) {
            setError(e?.response?.data?.error || 'Seznam se nepodařilo načíst.');
            setData(null);
        } finally {
            setLoading(false);
        }
    }, [rok, mesic]);

    useEffect(() => {
        if (!audit) load();
    }, [audit, load]);

    const toggle = async (row) => {
        setBusyKod(row.kod);
        setError('');
        try {
            if (row.moje && row.claim_id) {
                await api.delete(`/kategorie-zbozi/claim/${row.claim_id}/`);
            } else {
                await api.post('/kategorie-zbozi/claim/', { kod: row.kod, rok, mesic });
            }
            await load();
        } catch (e) {
            setError(e?.response?.data?.error || 'Odškrtnutí se neuložilo.');
        } finally {
            setBusyKod('');
        }
    };

    const openDetail = async (row) => {
        setDetail(row);
        setDetailItems([]);
        setDetailLoading(true);
        try {
            const res = await api.get('/kategorie-zbozi/polozky/', {
                params: { rok, mesic, kod: row.kod },
            });
            setDetailItems(res.data.polozky || []);
        } catch (e) {
            setError(e?.response?.data?.error || 'Položky se nepodařily načíst.');
        } finally {
            setDetailLoading(false);
        }
    };

    const move = (delta) => {
        const next = shiftMonth(rok, mesic, delta);
        setRok(next.rok);
        setMesic(next.mesic);
    };

    const radky = data?.radky || [];
    const cizi = radky.filter(jeCizi);
    const moje = radky.filter((row) => !jeCizi(row));

    if (audit && !isAdmin()) {
        return <Navigate to="/kategorie-zbozi" replace />;
    }

    return (
        <div className="kz-page">
            <PageHeader
                title="Kategorie zboží"
                subtitle={audit
                    ? 'Odškrtnuté kódy. Kategorie v prodejích se přepíše až po zaškrtnutí kontroly.'
                    : 'Odškrtni kód, až kategorii upravíš v Sympliu. Bod se připíše hned. Když noční kontrola zařazení nepotvrdí, bod se odečte.'}
                actions={(
                    <div className="kz-month">
                        <button type="button" onClick={() => move(-1)} aria-label="Předchozí měsíc">‹</button>
                        <span>{mesicLabel(rok, mesic)}</span>
                        <button type="button" onClick={() => move(1)} aria-label="Další měsíc">›</button>
                    </div>
                )}
            />
            {isAdmin() && (
                <Tabs
                    className="kz-tabs"
                    ariaLabel="Sekce kategorií zboží"
                    tabs={[
                        { id: 'seznam', label: 'K zařazení', to: '/kategorie-zbozi', end: true },
                        { id: 'audit', label: 'Audit', to: '/kategorie-zbozi/audit' },
                    ]}
                />
            )}
            {audit ? (
                <KategorieZboziAudit rok={rok} mesic={mesic} />
            ) : (
            <>
            <p className="kz-score">
                Tvoje body za tenhle měsíc: <strong>{data?.moje_body ?? 0}</strong>
            </p>
            {error && <p className="kz-error">{error}</p>}
            {loading && <p>Načítám produkty…</p>}
            {!loading && radky.length === 0 && (
                <p>V tomhle měsíci ve Zbytku žádný produkt s P kódem není.</p>
            )}
            {!loading && moje.length > 0 && (
                <ProductTable
                    rows={moje}
                    busyKod={busyKod}
                    onToggle={toggle}
                    onOpen={openDetail}
                />
            )}
            {!loading && cizi.length > 0 && (
                <details className="kz-cizi">
                    <summary>Řeší někdo jiný ({cizi.length})</summary>
                    <ProductTable
                        rows={cizi}
                        busyKod={busyKod}
                        onToggle={toggle}
                        onOpen={openDetail}
                    />
                </details>
            )}
            {detail && (
                <Modal title={`${detail.kod} · ${detail.nazev || ''}`} size="lg" onClose={() => setDetail(null)}>
                    {detailLoading && <p>Načítám doklady…</p>}
                    {!detailLoading && (
                        <table className="kz-table">
                            <thead>
                                <tr>
                                    <th>Datum</th>
                                    <th>Doklad</th>
                                    <th>Ks</th>
                                    <th>Prodejna</th>
                                </tr>
                            </thead>
                            <tbody>
                                {detailItems.map((p, idx) => (
                                    <tr key={`${p.doklad}-${idx}`}>
                                        <td>{p.datum || '—'}</td>
                                        <td>
                                            {p.objednavka ? (
                                                <a href={SYMPLIO_ORDER_URL(p.objednavka)} target="_blank" rel="noopener noreferrer">
                                                    {p.doklad || p.objednavka}
                                                </a>
                                            ) : (p.doklad || '—')}
                                        </td>
                                        <td>{p.pocet_kusu}</td>
                                        <td>{p.stredisko || '—'}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    )}
                </Modal>
            )}
            </>
            )}
        </div>
    );
}
