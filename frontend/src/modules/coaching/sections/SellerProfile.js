import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { coachingAPI } from '../../../services/api';
import { Tabs, Select } from '../../../components/ui';
import BenchmarkBadge from '../components/BenchmarkBadge';
import SignalsChips from '../components/SignalsChips';
import CoachingTimelineChart from '../components/CoachingTimelineChart';
import CategoryChart from '../components/CategoryChart';
import CoachingNotesPanel from '../components/CoachingNotesPanel';

const TABS = [
    { id: 'vykon', label: 'Výkon' },
    { id: 'kategorie', label: 'Kategorie' },
    { id: 'ukoly', label: 'Úkoly' },
    { id: 'porovnani', label: 'Porovnání' },
    { id: 'poznamky', label: 'Poznámky a cíle' },
];

const METRIC_OPTIONS = [
    { value: 'polozky_nad_100', label: 'Položky nad 100 Kč' },
    { value: 'sluzby_celkem', label: 'Služby' },
    { value: 'celkovy_obrat', label: 'Obrat' },
    { value: 'unikatni_doklady', label: 'Účtenky' },
];

const COMPARE_OPTS = [
    { value: '', label: 'Bez srovnání' },
    { value: 'prev_month', label: 'vs minulý měsíc' },
    { value: 'prev_quarter', label: 'vs minulý kvartál' },
    { value: 'prev_year', label: 'vs minulý rok' },
    { value: 'store_avg', label: 'vs průměr prodejny' },
    { value: 'store_top', label: 'vs top prodejce' },
];

const fmtPct = (v) => (v == null ? '—' : `${v}%`);
const fmtNum = (v) => Number(v || 0).toLocaleString('cs-CZ');

const SellerProfile = ({ staffUsers = [], mesic, onMesicChange }) => {
    const { userId } = useParams();
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();
    const effectiveMesic = searchParams.get('mesic') || mesic;

    const [tab, setTab] = useState('vykon');
    const [profile, setProfile] = useState(null);
    const [notes, setNotes] = useState([]);
    const [goals, setGoals] = useState([]);
    const [tasks, setTasks] = useState([]);
    const [workload, setWorkload] = useState(null);
    const [loading, setLoading] = useState(true);
    const [chartMetric, setChartMetric] = useState('polozky_nad_100');
    const [compare, setCompare] = useState('prev_year');
    const [selectedKat, setSelectedKat] = useState(null);
    const [comparePeer, setComparePeer] = useState('');
    const [compareData, setCompareData] = useState(null);

    const loadProfile = useCallback(async () => {
        setLoading(true);
        try {
            const [rok, m] = effectiveMesic.split('-').map(Number);
            const res = await coachingAPI.getSellerProfile(userId, {
                mesic: effectiveMesic,
                rok,
                mesic_cislo: m,
            });
            setProfile(res.profile);
            setNotes(res.notes || []);
            setGoals(res.goals || []);
        } finally {
            setLoading(false);
        }
    }, [userId, effectiveMesic]);

    const loadTasks = useCallback(async () => {
        const [rok, m] = effectiveMesic.split('-').map(Number);
        const res = await coachingAPI.getSellerTasks(userId, { mesic: effectiveMesic, rok, mesic_cislo: m });
        setTasks(res.tasks || []);
        setWorkload({
            sla: res.sla || {},
            prodejce: res.prodejce || {},
            poznamka_proxy: res.poznamka_proxy,
        });
    }, [userId, effectiveMesic]);

    useEffect(() => { loadProfile(); }, [loadProfile]);
    useEffect(() => {
        if (tab === 'ukoly') loadTasks();
    }, [tab, loadTasks]);

    useEffect(() => {
        if (!comparePeer) {
            setCompareData(null);
            return;
        }
        const [rok, m] = effectiveMesic.split('-').map(Number);
        coachingAPI.compareSellers({
            user_a: userId,
            user_b: comparePeer,
            mesic: effectiveMesic,
            rok,
            mesic_cislo: m,
        }).then((res) => setCompareData(res));
    }, [comparePeer, userId, effectiveMesic]);

    const peers = useMemo(
        () => staffUsers.filter((u) => String(u.id) !== String(userId)),
        [staffUsers, userId],
    );
    const compareSeller = useMemo(
        () => peers.find((u) => String(u.id) === comparePeer),
        [peers, comparePeer],
    );

    const peerOptions = useMemo(() => {
        const seller = profile?.prodejce;
        return [
            {
                value: '',
                label: seller ? `Jen ${seller.jmeno} ${seller.prijmeni}`.trim() : 'Jen prodejce',
            },
            ...peers.map((u) => ({
                value: String(u.id),
                label: `${u.jmeno} ${u.prijmeni}`,
            })),
        ];
    }, [peers, profile?.prodejce]);

    if (loading && !profile) return <p className="coaching-muted">Načítám profil…</p>;
    if (!profile) return <p className="coaching-muted">Prodejce nenalezen</p>;

    const p = profile.prodejce;
    const plneni = profile.plneni || {};
    const prodej = profile.prodej || {};
    const sla = workload?.sla || {};
    const wl = workload?.prodejce || {};

    return (
        <div className="coaching-profile">
            <header className="coaching-profile-header">
                <div>
                    <button type="button" className="coaching-back" onClick={() => navigate('/coaching')}>
                        ← Zpět na tým
                    </button>
                    <h2>{p.jmeno} {p.prijmeni}</h2>
                    <p className="coaching-muted">{p.prodejna} · {p.role}</p>
                    <SignalsChips signaly={profile.signaly} />
                    <BenchmarkBadge benchmark={profile.benchmark} />
                </div>
            </header>

            <Tabs
                tabs={TABS}
                activeId={tab}
                onTabChange={setTab}
                ariaLabel="Sekce profilu prodejce"
                className="coaching-profile-tabs"
            />

            {tab === 'vykon' && (
                <section className="coaching-panel">
                    <div className="coaching-kpi-grid">
                        <div className="coaching-kpi"><span>Plnění plánu</span><strong>{fmtPct(plneni.plneni_procent_kusy)}</strong></div>
                        <div className="coaching-kpi"><span>Obrat</span><strong>{fmtNum(plneni.obrat)} Kč</strong></div>
                        <div className="coaching-kpi"><span>Položky 100+</span><strong>{fmtNum(prodej.polozky_nad_100)}</strong></div>
                        <div className="coaching-kpi"><span>Účtenky</span><strong>{fmtNum(prodej.unikatni_doklady)}</strong></div>
                    </div>
                    <div className="coaching-chart-controls">
                        <Select
                            options={METRIC_OPTIONS}
                            value={chartMetric}
                            onChange={setChartMetric}
                            aria-label="Metrika grafu"
                        />
                        <Select
                            options={COMPARE_OPTS}
                            value={compare}
                            onChange={setCompare}
                            aria-label="Srovnání období"
                        />
                    </div>
                    <CoachingTimelineChart
                        userId={userId}
                        metric={chartMetric}
                        mesic={effectiveMesic}
                        compare={compare || undefined}
                        primaryLabel={`${p.jmeno} ${p.prijmeni}`.trim()}
                    />
                </section>
            )}

            {tab === 'kategorie' && (
                <section className="coaching-panel">
                    <p className="coaching-kat-hint">
                        Příslušenství je rozpadlé na podkategorie (Skla, Obaly, Ostatní).
                        Řádek „Příslušenství celkem“ je součet těchto tří – nadřazená kategorie v prodeji nemá vlastní kusy.
                    </p>
                    <div className="coaching-kat-grid">
                        {(profile.kategorie || []).map((k) => (
                            <button
                                key={k.kategorie_kod}
                                type="button"
                                className={`coaching-kat-card${k.je_souhrn ? ' coaching-kat-card--souhrn' : ''}${selectedKat === k.kategorie_kod ? ' coaching-kat-card--active' : ''}`}
                                onClick={() => setSelectedKat(k.kategorie_kod)}
                            >
                                <strong>{k.nazev}</strong>
                                <span>{k.skutecne_kusy} ks</span>
                                <span>{fmtPct(k.plneni_procent)} plánu</span>
                            </button>
                        ))}
                    </div>
                    {selectedKat && (
                        <CategoryChart
                            userId={userId}
                            kategorieKod={selectedKat}
                            nazev={(profile.kategorie || []).find((k) => k.kategorie_kod === selectedKat)?.nazev}
                            mesic={effectiveMesic}
                        />
                    )}
                </section>
            )}

            {tab === 'ukoly' && (
                <section className="coaching-panel">
                    <div className="coaching-kpi-grid">
                        <div className="coaching-kpi"><span>Hotovo</span><strong>{wl.pocet_ukolu_hotovo ?? 0}</strong></div>
                        <div className="coaching-kpi"><span>Včas %</span><strong>{sla.podil_vcas != null ? `${Math.round(sla.podil_vcas * 100)}%` : '—'}</strong></div>
                        <div className="coaching-kpi"><span>Index vytížení</span><strong>{wl.index_vytizeni ?? '—'}</strong></div>
                    </div>
                    <table className="coaching-tasks-table">
                        <thead>
                            <tr>
                                <th>Úkol</th>
                                <th>Priorita</th>
                                <th>Deadline</th>
                                <th>Dokončeno</th>
                                <th>Včas</th>
                            </tr>
                        </thead>
                        <tbody>
                            {tasks.map((t) => (
                                <tr key={t.id}>
                                    <td>{t.ukol}</td>
                                    <td>{t.priorita}</td>
                                    <td>{t.deadline || '—'}</td>
                                    <td>{t.dokonceno_v ? new Date(t.dokonceno_v).toLocaleString('cs-CZ') : '—'}</td>
                                    <td>{t.vcas == null ? '—' : t.vcas ? 'Ano' : 'Ne'}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </section>
            )}

            {tab === 'porovnani' && (
                <section className="coaching-panel">
                    <label className="coaching-nav-filter">
                        <span>Porovnat s (volitelně)</span>
                        <Select
                            options={peerOptions}
                            value={comparePeer}
                            onChange={setComparePeer}
                            aria-label="Porovnat s prodejcem"
                        />
                    </label>
                    <div className="coaching-chart-controls">
                        <Select
                            options={METRIC_OPTIONS}
                            value={chartMetric}
                            onChange={setChartMetric}
                            aria-label="Metrika grafu"
                        />
                        <Select
                            options={COMPARE_OPTS}
                            value={compare}
                            onChange={setCompare}
                            aria-label="Srovnání období"
                        />
                    </div>
                    <CoachingTimelineChart
                        userId={userId}
                        peerUserId={comparePeer || undefined}
                        primaryLabel={`${p.jmeno} ${p.prijmeni}`.trim()}
                        peerLabel={compareSeller ? `${compareSeller.jmeno} ${compareSeller.prijmeni}`.trim() : ''}
                        metric={chartMetric}
                        mesic={effectiveMesic}
                        compare={compare || undefined}
                    />
                    {compareData?.metriky && comparePeer && (
                        <table className="coaching-compare-table">
                            <thead>
                                <tr>
                                    <th>Metrika</th>
                                    <th>{compareData.prodejce_a?.jmeno} {compareData.prodejce_a?.prijmeni}</th>
                                    <th>{compareData.prodejce_b?.jmeno} {compareData.prodejce_b?.prijmeni}</th>
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
                </section>
            )}

            {tab === 'poznamky' && (
                <CoachingNotesPanel
                    prodejceId={Number(userId)}
                    notes={notes}
                    goals={goals}
                    onRefresh={loadProfile}
                />
            )}
        </div>
    );
};

export default SellerProfile;
