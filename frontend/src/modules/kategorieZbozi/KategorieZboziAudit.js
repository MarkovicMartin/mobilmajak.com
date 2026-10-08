import React, { useCallback, useEffect, useState } from 'react';
import api from '../../services/api';

const SYMPLIO_KATALOG_URL = (kod) =>
    `https://www.mobilmajak.cz/admin/katalog/vyhledavani?p%5Bhledat%5D=${encodeURIComponent(kod)}`;

const formatWhen = (iso) => {
    if (!iso) return '—';
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return '—';
    return d.toLocaleString('cs-CZ', { dateStyle: 'short', timeStyle: 'short' });
};

function AuditTable({ rows, busy, onToggle, onToggleAll }) {
    return (
        <table className="kz-table">
            <thead>
                <tr>
                    <th>
                        {onToggleAll && (
                            <input
                                type="checkbox"
                                checked={false}
                                disabled={busy || rows.length === 0}
                                onChange={onToggleAll}
                                aria-label="Označit vše jako zkontrolované"
                                title="Označit vše"
                            />
                        )}
                    </th>
                    <th>P kód</th>
                    <th>Název</th>
                    <th>Prodejce</th>
                    <th>Odškrtnuto</th>
                    <th>Předtím</th>
                    <th>Po kontrole</th>
                    <th>Databáze</th>
                </tr>
            </thead>
            <tbody>
                {rows.map((row) => (
                    <tr key={row.id}>
                        <td>
                            <input
                                type="checkbox"
                                checked={row.zkontrolovano}
                                disabled={busy}
                                onChange={() => onToggle(row)}
                                aria-label={`Zkontrolováno ${row.kod}`}
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
                        <td>{row.nazev || '—'}</td>
                        <td>{row.prodejce || '—'}</td>
                        <td>{formatWhen(row.vytvoreno)}</td>
                        <td>{row.kategorie_pred || '—'}</td>
                        <td>
                            {row.kategorie_po || '—'}
                            {row.poznamka ? <div className="kz-note">{row.poznamka}</div> : null}
                        </td>
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

export default function KategorieZboziAudit({ rok, mesic }) {
    const [rows, setRows] = useState([]);
    const [loading, setLoading] = useState(true);
    const [busy, setBusy] = useState(false);
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

    const mark = async (ids, zkontrolovano) => {
        if (!ids.length) return;
        setBusy(true);
        setError('');
        try {
            const res = await api.post('/kategorie-zbozi/audit/kontrola/', { ids, zkontrolovano });
            const idSet = new Set(ids);
            const prepsane = new Set(res.data.prepsano_ids || []);
            setRows((list) => list.map((row) => (
                idSet.has(row.id)
                    ? { ...row, zkontrolovano, prepsano: row.prepsano || prepsane.has(row.id) }
                    : row
            )));
        } catch (e) {
            setError(e?.response?.data?.error || 'Kontrolu se nepodařilo uložit.');
        } finally {
            setBusy(false);
        }
    };

    if (loading) return <p>Načítám audit…</p>;
    if (error && rows.length === 0) return <p className="kz-error">{error}</p>;

    const ceka = rows.filter((row) => !row.zkontrolovano);
    const hotovo = rows.filter((row) => row.zkontrolovano);

    return (
        <>
            {error && <p className="kz-error">{error}</p>}
            {ceka.length === 0 && (
                <p>V tomhle měsíci není nic ke kontrole.</p>
            )}
            {ceka.length > 0 && (
                <AuditTable
                    rows={ceka}
                    busy={busy}
                    onToggle={(row) => mark([row.id], true)}
                    onToggleAll={() => mark(ceka.map((row) => row.id), true)}
                />
            )}
            {hotovo.length > 0 && (
                <details className="kz-skryte">
                    <summary>Už zkontrolováno ({hotovo.length})</summary>
                    <AuditTable
                        rows={hotovo}
                        busy={busy}
                        onToggle={(row) => mark([row.id], false)}
                    />
                </details>
            )}
        </>
    );
}
