import React from 'react';
import { useNavigate } from 'react-router-dom';
import SignalsChips from '../components/SignalsChips';
import BenchmarkBadge from '../components/BenchmarkBadge';

const fmtPct = (v) => (v == null ? '—' : `${v}%`);
const fmtNum = (v) => (v == null ? '—' : Number(v).toLocaleString('cs-CZ'));

const trafficClass = (row) => {
    if (row.signaly?.systematicky_pod_planem) return 'coaching-row--bad';
    if ((row.signaly?.silne_kategorie || []).length >= 2) return 'coaching-row--good';
    if (row.plneni_procent_kusy != null && row.plneni_procent_kusy < 70) return 'coaching-row--warn';
    return '';
};

const TeamRoster = ({ prodejci, loading, mesic, error }) => {
    const navigate = useNavigate();

    if (loading) return <p className="coaching-muted">Načítám tým…</p>;
    if (error) return <p className="coaching-error">{error}</p>;
    if (!prodejci?.length) return <p className="coaching-muted">Žádní prodejci v tomto období</p>;

    return (
        <div className="coaching-roster-wrap">
            <table className="coaching-roster">
                <thead>
                    <tr>
                        <th>Prodejce</th>
                        <th>Prodejna</th>
                        <th>Plnění plánu</th>
                        <th>Signály</th>
                        <th>Položky 100+</th>
                        <th>Úkoly hotovo</th>
                        <th>Pořadí</th>
                        <th>Cíle</th>
                    </tr>
                </thead>
                <tbody>
                    {prodejci.map((row) => (
                        <tr
                            key={row.id}
                            className={`coaching-row ${trafficClass(row)}`}
                            onClick={() => navigate(`/coaching/seller/${row.id}?mesic=${mesic}`)}
                            tabIndex={0}
                            onKeyDown={(e) => e.key === 'Enter' && navigate(`/coaching/seller/${row.id}?mesic=${mesic}`)}
                        >
                            <td>
                                <strong>{row.prodejce}</strong>
                                <span className="coaching-row-role">{row.role}</span>
                            </td>
                            <td>{row.prodejna}</td>
                            <td>{fmtPct(row.plneni_procent_kusy)}</td>
                            <td><SignalsChips signaly={row.signaly} /></td>
                            <td>{fmtNum(row.polozky_nad_100)}</td>
                            <td>{fmtNum(row.ukoly_hotovo)}</td>
                            <td>
                                <BenchmarkBadge benchmark={row.benchmark} />
                            </td>
                            <td>{row.otevrene_cile || 0}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
};

export default TeamRoster;
