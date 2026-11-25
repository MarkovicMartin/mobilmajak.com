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

export default function KategorieZboziAutomatizace() {
    const [stav, setStav] = useState('otevreno');
    const [radky, setRadky] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [busyId, setBusyId] = useState(null);

    const load = useCallback(async () => {
        setLoading(true);
        setError('');
        try {
            const res = await api.get('/kategorie-zbozi/automatizace/', { params: { stav } });
            setRadky(res.data.radky || []);
        } catch (e) {
            setError(e?.response?.data?.error || 'Problémy se nepodařilo načíst.');
            setRadky([]);
        } finally {
            setLoading(false);
        }
    }, [stav]);

    useEffect(() => {
        load();
    }, [load]);

    const vyresit = async (row) => {
        setBusyId(row.id);
        setError('');
        try {
            await api.post(`/kategorie-zbozi/automatizace/${row.id}/vyresit/`);
            await load();
        } catch (e) {
            setError(e?.response?.data?.error || 'Vyřešení se neuložilo.');
        } finally {
            setBusyId(null);
        }
    };

    return (
        <div>
            <p className="kz-note">
                Sobotní zpracování bere jen skladem z Katalog / !Import / PARTNER PL
                a prázdného dodavatele nastaví na PARTNER PL.
                Sem padá to, co automat sám nedoplní: fotka, cena, popis, chybějící list.
            </p>
            <div className="kz-month kz-filter">
                <button type="button" onClick={() => setStav('otevreno')} disabled={stav === 'otevreno'}>
                    Otevřené
                </button>
                <button type="button" onClick={() => setStav('vyreseno')} disabled={stav === 'vyreseno'}>
                    Vyřešené
                </button>
            </div>
            {error && <p className="kz-error">{error}</p>}
            {loading && <p>Načítám problémy…</p>}
            {!loading && radky.length === 0 && <p>Žádné záznamy.</p>}
            {!loading && radky.length > 0 && (
                <table className="kz-table">
                    <thead>
                        <tr>
                            <th>P kód</th>
                            <th>Název</th>
                            <th>Typ</th>
                            <th>Problém</th>
                            <th>Zapsáno</th>
                            <th></th>
                        </tr>
                    </thead>
                    <tbody>
                        {radky.map((row) => (
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
                                <td>{row.typ_label}</td>
                                <td>{row.text}</td>
                                <td>
                                    {formatWhen(row.vytvoreno)}
                                    {row.vyresil ? <div className="kz-note">{row.vyresil}</div> : null}
                                </td>
                                <td>
                                    {row.stav === 'otevreno' && (
                                        <button
                                            type="button"
                                            className="kz-link"
                                            disabled={busyId === row.id}
                                            onClick={() => vyresit(row)}
                                        >
                                            Vyřešeno
                                        </button>
                                    )}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            )}
        </div>
    );
}
