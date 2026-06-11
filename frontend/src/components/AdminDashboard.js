import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { formatNewsAge } from '../utils/formatNewsAge';
import { format, getDaysInMonth } from 'date-fns';
import { useAuth } from '../context/AuthContext';
import api, { analyticsAPI, newsAPI, shiftsAPI, plansAPI } from '../services/api';
import { castkaBezDphZCelkem } from '../utils/dph';
import { PageHeader } from './ui';
import TodayWorkBoard from './TodayWorkBoard';
import DashboardTasksSnapshot from './DashboardTasksSnapshot';
import DashboardModuleHub from './DashboardModuleHub';
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
    const workBoardRef = useRef(null);

    const [todayStats, setTodayStats] = useState(null);
    const [monthStats, setMonthStats] = useState(null);
    const [todayShifts, setTodayShifts] = useState([]);
    const [latestNews, setLatestNews] = useState([]);
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
            const data = await shiftsAPI.listByMonth(currentMonth);
            const onlyToday = (data || []).filter((s) => s.datum?.startsWith(todayStr));
            setTodayShifts(onlyToday);
        };

        const fetchNews = async () => {
            const list = (await newsAPI.list() || []).slice(0, 3);
            setLatestNews(list);
        };

        const fetchPlanDashboard = async () => {
            try {
                const y = today.getFullYear();
                const m = today.getMonth() + 1;
                const res = await plansAPI.getPlneni(y, m);
                if (res?.plan && res?.plneni) {
                    setPlanDashboardBundle({ plan: res.plan, plneni: res.plneni });
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
                const res = await plansAPI.getPlneniProdejci(y, m);
                setPlanProdejciList(Array.isArray(res?.prodejci) ? res.prodejci : []);
            } catch (_e) {
                setPlanProdejciList([]);
            }
        };

        // Nastav CSRF cookie (pro pozdější POST)
        api.get('/csrf/').catch(() => {});

        fetchStats();
        fetchShifts();
        fetchNews();
        fetchPlanDashboard();
        fetchPlanProdejci();
    }, [isAdmin, currentMonth, todayStr, today]);

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

    const goPlansProdejny = () => navigate('/plans/plneni-prodejny');
    const goPlansProdejci = () => navigate('/plans/plneni-prodejci');
    const goAnalyticsCelkova = () => navigate('/analytics/celkova-cisla');

    const openShiftsSection = () => {
        workBoardRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    };

    const tileKeyActivate = (fn) => (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            fn();
        }
    };

    const goOrders = () => navigate('/orders');

    if (!isAdmin()) return null;

    const shiftStoreCount = new Set(
        todayShifts.map((s) => s.prodejna || s.prodejna_nazev).filter(Boolean)
    ).size;

    return (
        <div className="admin-dashboard">
            <div className="container">
                <PageHeader title="Přehled" />
                <DashboardModuleHub />
                {planMetrics && (
                    <div className="plan-tiles-row">
                        <div
                            className="tile tile--plan tile--clickable"
                            role="button"
                            tabIndex={0}
                            onClick={goPlansProdejny}
                            onKeyDown={tileKeyActivate(goPlansProdejny)}
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
                            onClick={goPlansProdejny}
                            onKeyDown={tileKeyActivate(goPlansProdejny)}
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
                    <div className="tile-sub">Prodejny: {shiftStoreCount}</div>
                </div>
                <div
                    className="tile tile--clickable"
                    role="button"
                    tabIndex={0}
                    onClick={goOrders}
                    onKeyDown={tileKeyActivate(goOrders)}
                >
                    <div className="tile-title">Objednávky</div>
                    <div className="tile-value">
                        <i className="fas fa-shopping-cart" aria-hidden="true" />
                    </div>
                    <div className="tile-sub">Kanban a správa objednávek →</div>
                </div>
                </div>

                <div className="content-stack">
                    <div ref={workBoardRef}>
                        <TodayWorkBoard today={today} />
                    </div>

                    <DashboardTasksSnapshot />

                    <div className="card">
                        <div className="card-header">
                            <div className="card-title">Nejnovější novinky</div>
                        </div>
                        <div className="news-list">
                            {latestNews.map((n) => (
                                <Link to={`/news#post-${n.id}`} className="news-item news-item-link" key={n.id}>
                                    <div className="news-content">{n.obsah?.slice(0, 140) || ''}</div>
                                    <div className="news-item-meta">{formatNewsAge(n.datum_vytvoreni)}</div>
                                </Link>
                            ))}
                            {latestNews.length === 0 && <div className="muted">Žádné novinky</div>}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}


