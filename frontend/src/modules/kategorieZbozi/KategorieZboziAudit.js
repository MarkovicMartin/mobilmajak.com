import React, { useCallback, useEffect, useState } from 'react';
import api from '../../services/api';

const SYMPLIO_KATALOG_URL = (kod) =>
    `https://www.mobilmajak.cz/admin/katalog/vyhledavani?p%5Bhledat%5D=${encodeURIComponent(kod)}`;

const STAV_LABEL = {
    ceka: 'Čeká na noční kontrolu',
    potvrzeno: 'V plánu, bod připsán',
    nepotvrzeno: 'Mimo plán',
};

const formatWhen = (iso) => {
    if (!iso) return '—';
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return '—';
    return d.toLocaleString('cs-CZ', { dateStyle: 'short', timeStyle: 'short' });
};

export default function KategorieZboziAudit({ rok, mesic }) {
    const [rows, setRows] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    const load = useCallback(async () => {
        setLoading(true);
        setError('');
        try {
            const res = await api.get('/kategorie-zbozi/audit/', { params: { rok, mesic } });
            setRows(res.data.radky || []);
        } catch (e) {
            setError(e?.response?.data?.error || 'Audit se nepodařilo načíst.');
            setRows([]);
        } finally {
            setLoading(false);
        }
    }, [rok, mesic]);

    useEffect(() => { load(); }, [load]);

    if (loading) return <p>Načítám audit…</p>;
    if (error) return <p className="kz-error">{error}</p>;
    if (rows.length === 0) return <p>V tomhle měsíci nikdo žádný kód neodškrtl.</p>;

    return (
        <table className="kz-table">
            <thead>
                <tr>
                    <th>P kód</th>
                    <th>Název</th>
                    <th>Prodejce</th>
                    <th>Odškrtnuto</th>
                    <th>Předtím</th>
                    <th>Po kontrole</th>
                    <th>Stav</th>
                    <th>Databáze</th>
                </tr>
            </thead>
            <tbody>
                {rows.map((row) => (
                    <tr key={row.id}>
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
                        <td>{row.nazev || '—'}</td>
                        <td>{row.prodejce || '—'}</td>
                        <td>{formatWhen(row.vytvoreno)}</td>
                        <td>{row.kategorie_pred || '—'}</td>
                        <td>
                            {row.kategorie_po || '—'}
                            {row.poznamka ? <div className="kz-note">{row.poznamka}</div> : null}
                        </td>
                        <td>{STAV_LABEL[row.stav] || row.stav}</td>
                        <td>
                            {row.prepsano ? (
                                <span className="kz-badge kz-badge-prepsano">Přepsáno</span>
                            ) : (
                                <span className="kz-note">Zatím ne</span>
                            )}
                        </td>
                    </tr>
                ))}
            </tbody>
        </table>
    );
}
