import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { format, getDaysInMonth } from 'date-fns';
import { cs } from 'date-fns/locale';
import { useAuth } from '../context/AuthContext';
import api, { analyticsAPI, userAPI } from '../services/api';
import { castkaBezDphZCelkem } from '../utils/dph';
import './AdminDashboard.css';

const currency = (num) =>
    new Intl.NumberFormat('cs-CZ', { style: 'currency', currency: 'CZK', maximumFractionDigits: 0 }).format(
        Number(num || 0)
    );

/** 1 prodejna, 2–4 prodejny, 5+ prodejen */
const prodejenWord = (n) => {
    if (n === 1) return 'prodejna';
    if (n >= 2 && n <= 4) return 'prodejny';
    return 'prodejen';
};

/** Rozdíl oproti 100 % cíle: zeleně / žlutě / červeně */
const planTrendClass = (deltaPct) => {
    if (deltaPct == null || Number.isNaN(deltaPct)) return '';
    if (deltaPct >= 0) return 'plan-tile-trend--ok';
    if (deltaPct >= -20) return 'plan-tile-trend--warn';
    return 'plan-tile-trend--bad';
};

/** Absolutní plnění trend % (vyšší = lépe) */
const planPctClass = (pct) => {
    if (pct == null || Number.isNaN(pct)) return '';
    if (pct >= 100) return 'plan-tile-pct--ok';
    if (pct >= 80) return 'plan-tile-pct--warn';
    return 'plan-tile-pct--bad';
};

export default function AdminDashboard() {
    const { isAdmin } = useAuth();
    const navigate = useNavigate();
    const shiftsDetailsRef = useRef(null);

    const [todayStats, setTodayStats] = useState(null);
    const [monthStats, setMonthStats] = useState(null);
    const [todayShifts, setTodayShifts] = useState([]);
    const [latestNews, setLatestNews] = useState([]);
    const [tasks, setTasks] = useState([]);
    const [users, setUsers] = useState([]);
    const [newTask, setNewTask] = useState({ ukol: '', priorita: 'stredni', deadline: '', id_prodejce_ukol: '' });
    const [planDashboardBundle, setPlanDashboardBundle] = useState(null);
    const [planProdejciList, setPlanProdejciList] = useState([]);

    const today = useMemo(() => new Date(), []);
    const currentMonth = useMemo(() => format(today, 'yyyy-MM'), [today]);
    const todayStr = useMemo(() => format(today, 'yyyy-MM-dd'), [today]);

    useEffect(() => {
        if (!isAdmin()) return;

        const fetchStats = async () => {
            // Dnešní
            const t = await api.get(`/analytics/celkova-cisla/?period=daily`);
            setTodayStats(t.data.aggregations || t.data);

            // Tento měsíc
            const m = await api.get(`/analytics/celkova-cisla/?period=monthly`);
            setMonthStats(m.data.aggregations || m.data);
        };

        const fetchShifts = async () => {
            const resp = await api.get(`/shifts/?mesic=${currentMonth}`);
            console.log('API odpověď směny:', resp.data); // Debug log
            const onlyToday = (resp.data || []).filter((s) => s.datum?.startsWith(todayStr));
            console.log('Dnešní směny:', onlyToday); // Debug log
            setTodayShifts(onlyToday);
        };

        const fetchNews = async () => {
            const resp = await api.get(`/news/`);
            const list = (resp.data || []).slice(0, 3);
            setLatestNews(list);
        };

        const fetchTasks = async () => {
            const resp = await api.get(`/tasks/?stav=vse`);
            setTasks(resp.data || []);
        };

        const fetchUsers = async () => {
            try {
                const payload = await userAPI.getUsers();
                const arr = Array.isArray(payload) ? payload : payload.users || [];
                setUsers(arr);
            } catch (_e) {
                setUsers([]);
            }
        };

        const fetchPlanDashboard = async () => {
            try {
                const y = today.getFullYear();
                const m = today.getMonth() + 1;
                const res = await api.get(`/plans/${y}/${m}/plneni/`);
                if (res.data?.plan && res.data?.plneni) {
                    setPlanDashboardBundle({ plan: res.data.plan, plneni: res.data.plneni });
                } else {
                    setPlanDashboardBundle(null);
                }
            } catch (_e) {
                setPlanDashboardBundle(null);
            }
        };

        const fetchPlanProdejci = async () => {
            try {
                const y = today.getFullYear();
                const m = today.getMonth() + 1;
                const res = await api.get(`/plans/${y}/${m}/plneni-prodejci/`);
                setPlanProdejciList(Array.isArray(res.data?.prodejci) ? res.data.prodejci : []);
            } catch (_e) {
                setPlanProdejciList([]);
            }
        };

        // Nastav CSRF cookie (pro pozdější POST)
        api.get('/csrf/').catch(() => {});

        fetchStats();
        fetchShifts();
        fetchNews();
        fetchTasks();
        fetchUsers();
        fetchPlanDashboard();
        fetchPlanProdejci();
    }, [isAdmin, currentMonth, todayStr, today]);

    const groupedShifts = useMemo(() => {
        const groups = {};
        console.log('Zpracovávám směny pro skupiny:', todayShifts); // Debug log
        todayShifts.forEach((s) => {
            console.log('Zpracovávám směnu:', s); // Debug log pro každou směnu
            const key = s.prodejna || 'Neznámá prodejna';
            if (!groups[key]) groups[key] = [];
            const full = [s.user?.jmeno, s.user?.prijmeni].filter(Boolean).join(' ').trim();
            console.log(`Jméno pro ${key}:`, full); // Debug log pro jméno
            groups[key].push(full || s.user_name || '');
        });
        console.log('Skupiny směn:', groups); // Debug log
        return groups;
    }, [todayShifts]);

    const userNameById = useMemo(() => {
        const map = {};
        (users || []).forEach((u) => {
            map[u.id] = [u.jmeno, u.prijmeni].filter(Boolean).join(' ').trim();
        });
        return map;
    }, [users]);

    const planMetrics = useMemo(() => {
        const plneni = planDashboardBundle?.plneni;
        const plan = planDashboardBundle?.plan;
        if (!plneni?.firma) return null;

        const firma = plneni.firma;
        const planObrat = parseFloat(String(firma.plan_obrat ?? '0'));
        const planObratBezDph = castkaBezDphZCelkem(planObrat);
        const daysInMonth = getDaysInMonth(today);
        const dailyTarget =
            planObratBezDph > 0 && daysInMonth > 0 ? planObratBezDph / daysInMonth : null;

        const todayActual = Number(todayStats?.celkovy_obrat_bez_dph) || 0;
        let dailyPct = null;
        if (dailyTarget != null && dailyTarget > 0) {
            dailyPct = (todayActual / dailyTarget) * 100;
        }
        const dailyDeltaVs100 = dailyPct != null ? dailyPct - 100 : null;

        const monthPct = typeof firma.plneni_procent === 'number' ? firma.plneni_procent : null;
        const monthTrendPct =
            firma.trend_procent != null ? firma.trend_procent : monthPct;

        let worstStore = null;
        const prodejnyMap = plneni.prodejny || {};
        if (plan?.prodejny?.length) {
            for (const [pidStr, pdata] of Object.entries(prodejnyMap)) {
                const score =
                    pdata.trend_procent != null ? pdata.trend_procent : pdata.plneni_procent;
                if (score == null || Number.isNaN(Number(score))) continue;
                const pid = Number(pidStr);
                if (!worstStore || Number(score) < Number(worstStore.score)) {
                    const ps = plan.prodejny.find((x) => x.prodejna_id === pid);
                    worstStore = {
                        score: Number(score),
                        nazev: ps?.prodejna_nazev || `Prodejna #${pid}`,
                    };
                }
            }
        }

        let worstSeller = null;
        for (const p of planProdejciList) {
            // U prodejců je plán vs. realita v kusích, ne v obratu (viz plán prodejců v modulu Plány)
            const score =
                p.trend_procent_kusy != null ? p.trend_procent_kusy : p.plneni_procent_kusy;
            if (score == null || Number.isNaN(Number(score))) continue;
            // 0 % často = ještě nebyla směna / jen výpomoc – nepočítat mezi „nejhorší“
            if (Number(score) === 0) continue;
            if (!worstSeller || Number(score) < Number(worstSeller.score)) {
                worstSeller = {
                    score: Number(score),
                    jmeno: [p.jmeno, p.prijmeni].filter(Boolean).join(' ').trim(),
                    prodejna: p.prodejna_nazev,
                };
            }
        }

        return {
            dailyTarget,
            dailyPct,
            dailyDeltaVs100,
            monthPct,
            monthTrendPct,
            planObratMonth: planObratBezDph,
            worstStore,
            worstSeller,
        };
    }, [planDashboardBundle, todayStats, today, planProdejciList]);

    const goPlansDefault = () =>
        navigate({ pathname: '/plans', hash: '' }, { state: { fromDashboardPlans: true } });
    const goPlansProdejny = () => navigate({ pathname: '/plans', hash: 'plneni-prodejny' });
    const goPlansProdejci = () => navigate({ pathname: '/plans', hash: 'plneni-prodejci' });
    const goAnalyticsCelkova = () => navigate('/analytics/celkova-cisla');

    const openShiftsSection = () => {
        const el = shiftsDetailsRef.current;
        if (el) {
            el.open = true;
            el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    };

    const tileKeyActivate = (fn) => (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            fn();
        }
    };

    const handleCreateTask = async (e) => {
        e.preventDefault();
        if (!newTask.ukol || !newTask.id_prodejce_ukol) return;
        const resp = await api.post('/tasks/', {
            ukol: newTask.ukol,
            priorita: newTask.priorita || 'stredni',
            deadline: newTask.deadline || null,
            id_prodejce_ukol: Number(newTask.id_prodejce_ukol),
        });
        setTasks((t) => [resp.data, ...t]);
        setNewTask({ ukol: '', priorita: 'stredni', deadline: '', id_prodejce_ukol: '' });
    };

    const markDone = async (taskId) => {
        const resp = await api.put(`/tasks/${taskId}/`, { stav: 'hotovo' });
        setTasks((list) => list.map((t) => (t.id === taskId ? resp.data : t)));
    };

    if (!isAdmin()) return null;

    const shiftStoreCount = Object.keys(groupedShifts).length;

    return (
        <div className="admin-dashboard">
            <div className="container">
                {planMetrics && (
                    <div className="plan-tiles-row">
                        <div
                            className="tile tile--plan tile--clickable"
                            role="button"
                            tabIndex={0}
                            onClick={goPlansDefault}
                            onKeyDown={tileKeyActivate(goPlansDefault)}
                        >
                            <div className="tile-title">Plnění dnes (vs cíl dne, bez DPH)</div>
                            <div
                                className={`tile-value plan-tile-pct ${planPctClass(planMetrics.dailyPct)}`}
                            >
                                {planMetrics.dailyPct != null
                                    ? `${planMetrics.dailyPct.toFixed(1)} %`
                                    : '–'}
                            </div>
                            <div
                                className={`tile-sub plan-tile-trend ${planTrendClass(
                                    planMetrics.dailyDeltaVs100
                                )}`}
                            >
                                {planMetrics.dailyDeltaVs100 != null
                                    ? `${planMetrics.dailyDeltaVs100 >= 0 ? '+' : ''}${planMetrics.dailyDeltaVs100.toFixed(
                                          1
                                      )} % k dennímu cíli (bez DPH)`
                                    : '–'}
                            </div>
                            <div className="tile-sub">
                                Cíl dne (bez DPH):{' '}
                                {planMetrics.dailyTarget != null
                                    ? currency(planMetrics.dailyTarget)
                                    : '–'}
                            </div>
                        </div>
                        <div
                            className="tile tile--plan tile--clickable"
                            role="button"
                            tabIndex={0}
                            onClick={goPlansDefault}
                            onKeyDown={tileKeyActivate(goPlansDefault)}
                        >
                            <div className="tile-title">Plnění měsíce (obrat bez DPH)</div>
                            <div
                                className={`tile-value plan-tile-pct ${planPctClass(planMetrics.monthPct)}`}
                            >
                                {planMetrics.monthPct != null
                                    ? `${planMetrics.monthPct.toFixed(1)} %`
                                    : '–'}
                            </div>
                            <div
                                className={`tile-sub plan-tile-trend ${planTrendClass(
                                    planMetrics.monthTrendPct != null
                                        ? planMetrics.monthTrendPct - 100
                                        : null
                                )}`}
                            >
                                Trend ~{' '}
                                {planMetrics.monthTrendPct != null
                                    ? `${planMetrics.monthTrendPct.toFixed(1)} %`
                                    : '–'}{' '}
                                na konec měsíce (bez DPH)
                            </div>
                            <div className="tile-sub">
                                Plán měsíce (bez DPH): {currency(planMetrics.planObratMonth)}
                            </div>
                        </div>
                        <div
                            className="tile tile--plan tile--clickable"
                            role="button"
                            tabIndex={0}
                            onClick={goPlansProdejny}
                            onKeyDown={tileKeyActivate(goPlansProdejny)}
                        >
                            <div className="tile-title">Nejslabší prodejna (trend, obrat bez DPH)</div>
                            <div
                                className={`tile-value plan-tile-pct ${
                                    planMetrics.worstStore ? planPctClass(planMetrics.worstStore.score) : ''
                                }`}
                            >
                                {planMetrics.worstStore
                                    ? `${planMetrics.worstStore.score.toFixed(1)} %`
                                    : '–'}
                            </div>
                            <div className="tile-sub tile-sub--ellipsis">
                                {planMetrics.worstStore?.nazev || '—'}
                            </div>
                        </div>
                        <div
                            className="tile tile--plan tile--clickable"
                            role="button"
                            tabIndex={0}
                            onClick={goPlansProdejci}
                            onKeyDown={tileKeyActivate(goPlansProdejci)}
                        >
                            <div className="tile-title">Nejslabší prodejce (trend, kusy)</div>
                            <div
                                className={`tile-value plan-tile-pct ${
                                    planMetrics.worstSeller ? planPctClass(planMetrics.worstSeller.score) : ''
                                }`}
                            >
                                {planMetrics.worstSeller
                                    ? `${planMetrics.worstSeller.score.toFixed(1)} %`
                                    : '–'}
                            </div>
                            <div className="tile-sub tile-sub--ellipsis">
                                {planMetrics.worstSeller
                                    ? `${planMetrics.worstSeller.jmeno} (${planMetrics.worstSeller.prodejna})`
                                    : '—'}
                            </div>
                        </div>
                    </div>
                )}
                <div className="tiles-row">
                <div
                    className="tile tile--clickable"
                    role="button"
                    tabIndex={0}
                    onClick={goAnalyticsCelkova}
                    onKeyDown={tileKeyActivate(goAnalyticsCelkova)}
                >
                    <div className="tile-title">Obrat dnes (bez DPH)</div>
                    <div className="tile-value">{currency(todayStats?.celkovy_obrat_bez_dph)}</div>
                    <div className="tile-sub">Marže dnes: {currency(todayStats?.celkovy_zisk)} ({todayStats?.marze_procenta || 0}%)</div>
                </div>
                <div
                    className="tile tile--clickable"
                    role="button"
                    tabIndex={0}
                    onClick={goAnalyticsCelkova}
                    onKeyDown={tileKeyActivate(goAnalyticsCelkova)}
                >
                    <div className="tile-title">Obrat tento měsíc (bez DPH)</div>
                    <div className="tile-value">{currency(monthStats?.celkovy_obrat_bez_dph)}</div>
                    <div className="tile-sub">Marže měsíc: {currency(monthStats?.celkovy_zisk)} ({monthStats?.marze_procenta || 0}%)</div>
                </div>
                <div
                    className="tile tile--clickable"
                    role="button"
                    tabIndex={0}
                    onClick={openShiftsSection}
                    onKeyDown={tileKeyActivate(openShiftsSection)}
                >
                    <div className="tile-title">Počet lidí dnes na směně</div>
                    <div className="tile-value">{todayShifts.length} lidí</div>
                    <div className="tile-sub">Prodejny: {Object.keys(groupedShifts).length}</div>
                </div>
                <div className="tile">
                    <div className="tile-title">Aktivní úkoly (celkem)</div>
                    <div className="tile-value">{tasks.filter((t) => t.stav !== 'hotovo').length}</div>
                    <div className="tile-sub">
                        {tasks.filter((t) => t.stav !== 'hotovo').length} otevřených
                    </div>
                </div>
                </div>

                <div className="content-stack">
                    <section className="shifts-section" aria-labelledby="shifts-heading">
                        <details className="shifts-details" ref={shiftsDetailsRef}>
                            <summary className="shifts-summary">
                                <span id="shifts-heading" className="shifts-section-title">
                                    Kdo je dnes v práci
                                </span>
                                <span className="shifts-summary-meta">
                                    <span className="badge badge--minimal">{format(today, 'd. MMM', { locale: cs })}</span>
                                    {shiftStoreCount > 0 && (
                                        <span className="shifts-count-pill">
                                            {shiftStoreCount} {prodejenWord(shiftStoreCount)}
                                        </span>
                                    )}
                                </span>
                            </summary>
                            <div className="shifts-tiles-wrap">
                                <div className="shifts-tiles">
                                    {Object.keys(groupedShifts).length === 0 && (
                                        <div className="muted shifts-empty">Žádné směny dnes</div>
                                    )}
                                    {Object.entries(groupedShifts).map(([store, people]) => (
                                        <div className="shift-tile" key={store}>
                                            <div className="shift-tile-store">{store}</div>
                                            <div className="shift-tile-people">{people.join(', ')}</div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </details>
                    </section>

                    <div className="card card--tasks">
                        <div className="card-header">
                            <div className="card-title">Úkoly – přehled</div>
                        </div>
                        <form className="task-form" onSubmit={handleCreateTask} style={{ overflow: 'visible' }}>
                            <input
                                className="input task-input"
                                placeholder="Zadat nový úkol… (např. Zkontrolovat sklad – Samsung)"
                                value={newTask.ukol}
                                onChange={(e) => setNewTask((t) => ({ ...t, ukol: e.target.value }))}
                            />
                            <select
                                className="select"
                                value={newTask.id_prodejce_ukol}
                                onChange={(e) => setNewTask((t) => ({ ...t, id_prodejce_ukol: e.target.value }))}
                            >
                                <option value="">Přiřadit prodejci…</option>
                                {users.map((u) => (
                                    <option key={u.id} value={u.id}>
                                        {[u.jmeno, u.prijmeni].filter(Boolean).join(' ').trim()}
                                    </option>
                                ))}
                            </select>
                            <button className="btn-primary" type="submit">
                                Přidat
                            </button>
                        </form>
                        <div className="tasks-list">
                            {tasks.length === 0 && <div className="muted">Žádné úkoly</div>}
                            {tasks[0] && (
                                <div className="task-item task-item--preview">
                                    <div>
                                        <div className="task-title">{tasks[0].ukol}</div>
                                        <div className="task-meta">
                                            Přiřazeno: {userNameById[tasks[0].id_prodejce_ukol] || tasks[0].id_prodejce_ukol} • Stav:{' '}
                                            {tasks[0].stav}
                                        </div>
                                    </div>
                                    {tasks[0].stav !== 'hotovo' && (
                                        <button type="button" className="btn-outline" onClick={() => markDone(tasks[0].id)}>
                                            Označit hotovo
                                        </button>
                                    )}
                                </div>
                            )}
                            {tasks.length > 1 && (
                                <details className="tasks-more">
                                    <summary className="tasks-more-summary">
                                        Další úkoly ({tasks.length - 1})
                                    </summary>
                                    <div className="tasks-more-list">
                                        {tasks.slice(1, 50).map((t) => (
                                            <div className="task-item" key={t.id}>
                                                <div>
                                                    <div className="task-title">{t.ukol}</div>
                                                    <div className="task-meta">
                                                        Přiřazeno: {userNameById[t.id_prodejce_ukol] || t.id_prodejce_ukol} • Stav: {t.stav}
                                                    </div>
                                                </div>
                                                {t.stav !== 'hotovo' && (
                                                    <button type="button" className="btn-outline" onClick={() => markDone(t.id)}>
                                                        Označit hotovo
                                                    </button>
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                </details>
                            )}
                        </div>
                    </div>

                    <div className="card">
                        <div className="card-header">
                            <div className="card-title">Nejnovější novinky</div>
                        </div>
                        <div className="news-list">
                            {latestNews.map((n) => (
                                <div className="news-item" key={n.id}>
                                    <div className="news-content">{n.obsah?.slice(0, 140) || ''}</div>
                                    <button type="button" className="btn-link">
                                        Otevřít
                                    </button>
                                </div>
                            ))}
                            {latestNews.length === 0 && <div className="muted">Žádné novinky</div>}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}


