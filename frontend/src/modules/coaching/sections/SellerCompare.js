import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { coachingAPI } from '../../../services/api';
import CoachingTimelineChart from '../components/CoachingTimelineChart';

const METRICS = [
    { key: 'polozky_nad_100', label: 'Položky nad 100 Kč' },
    { key: 'sluzby_celkem', label: 'Služby' },
    { key: 'celkovy_obrat', label: 'Obrat' },
    { key: 'unikatni_doklady', label: 'Účtenky' },
];

const COMPARE_OPTS = [
    { value: '', label: 'Bez srovnání období' },
    { value: 'prev_month', label: 'vs minulý měsíc' },
    { value: 'prev_quarter', label: 'vs minulý kvartál' },
    { value: 'prev_year', label: 'vs minulý rok' },
    { value: 'store_avg', label: 'vs průměr prodejny' },
    { value: 'store_top', label: 'vs top prodejce' },
];

const fmtNum = (v) => Number(v || 0).toLocaleString('cs-CZ');

const sellerName = (u) => (u ? `${u.jmeno || ''} ${u.prijmeni || ''}`.trim() : '');

const SellerCompare = ({ staffUsers = [], mesic }) => {
    const navigate = useNavigate();
    const [primaryId, setPrimaryId] = useState('');
    const [peerId, setPeerId] = useState('');
    const [metric, setMetric] = useState('polozky_nad_100');
    const [compare, setCompare] = useState('prev_year');
    const [compareData, setCompareData] = useState(null);
    const [loading, setLoading] = useState(false);

    const primary = useMemo(
        () => staffUsers.find((u) => String(u.id) === String(primaryId)),
        [staffUsers, primaryId],
    );
    const peer = useMemo(
        () => staffUsers.find((u) => String(u.id) === String(peerId)),
        [staffUsers, peerId],
    );
    const primaryName = sellerName(primary);
    const peerName = sellerName(peer);

    useEffect(() => {
        if (!primaryId || !peerId || peerId === primaryId) {
            setCompareData(null);
            return;
        }
        let cancelled = false;
        const load = async () => {
            setLoading(true);
            try {
                const [rok, m] = mesic.split('-').map(Number);
                const cmpRes = await coachingAPI.compareSellers({
                    user_a: primaryId,
                    user_b: peerId,
                    mesic,
                    rok,
                    mesic_cislo: m,
                });
                if (!cancelled) setCompareData(cmpRes);
            } finally {
                if (!cancelled) setLoading(false);
            }
        };
        load();
        return () => { cancelled = true; };
    }, [primaryId, peerId, mesic]);

    const peerOptions = staffUsers.filter((u) => String(u.id) !== String(primaryId));

    return (
        <section className="coaching-panel coaching-analysis">
            <p className="coaching-analysis-hint">
                Vyberte prodejce pro vývoj v čase. Druhého prodejce můžete přidat pro srovnání v grafu i tabulce.
            </p>
            <div className="coaching-compare-pickers">
                <label className="coaching-nav-filter">
                    <span>Prodejce</span>
                    <select value={primaryId} onChange={(e) => setPrimaryId(e.target.value)}>
                        <option value="">Vyberte prodejce…</option>
                        {staffUsers.map((u) => (
                            <option key={u.id} value={u.id}>{sellerName(u)}</option>
                        ))}
                    </select>
                </label>
                <label className="coaching-nav-filter">
                    <span>Porovnat s (volitelně)</span>
                    <select value={peerId} onChange={(e) => setPeerId(e.target.value)}>
                        <option value="">Jen jeden prodejce</option>
                        {peerOptions.map((u) => (
                            <option key={u.id} value={u.id}>{sellerName(u)}</option>
                        ))}
                    </select>
                </label>
            </div>

            {!primaryId && (
                <p className="coaching-muted">Začněte výběrem prodejce – zobrazí se graf vývoje za posledních 12 měsíců.</p>
            )}

            {primaryId && (
                <>
                    <div className="coaching-analysis-header">
                        <div>
                            <h3>{primaryName}</h3>
                            {peerId && peerName && (
                                <p className="coaching-muted">Srovnání s {peerName}</p>
                            )}
                        </div>
                        <button
                            type="button"
                            className="coaching-link-btn"
                            onClick={() => navigate(`/coaching/seller/${primaryId}?mesic=${mesic}`)}
                        >
                            Otevřít detail →
                        </button>
                    </div>

                    <div className="coaching-chart-controls">
                        <select value={metric} onChange={(e) => setMetric(e.target.value)}>
                            {METRICS.map((m) => <option key={m.key} value={m.key}>{m.label}</option>)}
                        </select>
                        <select value={compare} onChange={(e) => setCompare(e.target.value)}>
                            {COMPARE_OPTS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                        </select>
                    </div>

                    <CoachingTimelineChart
                        userId={primaryId}
                        peerUserId={peerId || undefined}
                        primaryLabel={primaryName}
                        peerLabel={peerName}
                        metric={metric}
                        mesic={mesic}
                        compare={compare || undefined}
                    />

                    {loading && peerId && <p className="coaching-muted">Načítám srovnání…</p>}

                    {compareData?.metriky && (
                        <table className="coaching-compare-table">
                            <thead>
                                <tr>
                                    <th>Metrika ({mesic})</th>
                                    <th>{primaryName}</th>
                                    <th>{peerName}</th>
                                </tr>
                            </thead>
                            <tbody>
                                {compareData.metriky.map((row) => (
                                    <tr key={row.metric}>
                                        <td>{row.label}</td>
                                        <td>{fmtNum(row.a)}</td>
                                        <td>{fmtNum(row.b)}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    )}

                    {compareData?.kategorie?.length > 0 && (
                        <>
                            <h4>Kategorie v měsíci</h4>
                            <table className="coaching-compare-table">
                                <thead>
                                    <tr>
                                        <th>Kategorie</th>
                                        <th>{primaryName}</th>
                                        <th>{peerName}</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {compareData.kategorie.map((row) => (
                                        <tr key={row.kategorie_kod}>
                                            <td>{row.nazev}</td>
                                            <td>{fmtNum(row.a_kusy)} ks</td>
                                            <td>{fmtNum(row.b_kusy)} ks</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </>
                    )}
                </>
            )}
        </section>
    );
};

export default SellerCompare;
