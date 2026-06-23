import React, { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { formatNewsAge } from '../utils/formatNewsAge';
import { plansAPI, newsAPI, shiftsAPI } from '../services/api';
import { useSalespersonMetrics } from '../hooks/useSalespersonMetrics';
import { PageHeader, Select, SegmentControl } from './ui';
import DashboardModuleHub from './DashboardModuleHub';
import './SellerDashboard.css';
import AttendancePanel from '../modules/shifts/AttendancePanel';

const number = (v) => (v ?? 0).toLocaleString('cs-CZ');
const trendTrida = (pct) => {
  if (pct == null) return '';
  if (pct >= 100) return 'muj-plan-trend-ok';
  if (pct >= 80) return 'muj-plan-trend-var';
  return 'muj-plan-trend-chyba';
};
const fmtDelta = (v, suffix = '') => {
  if (v == null) return '';
  const sign = v > 0 ? '+' : '';
  return `${sign}${(typeof v === 'number' ? v.toLocaleString('cs-CZ') : v)}${suffix}`;
};

function MetricCard({ title, value, sub, delta }) {
  return (
    <div className="metric-card">
      <div className="metric-title">{title}</div>
      <div className="metric-value">{value}</div>
      <div className="metric-chip">vs. minulý {delta}</div>
      {sub && <div className="metric-sub">{sub}</div>}
    </div>
  );
}

export default function SellerDashboard({ user }) {
  const navigate = useNavigate();
  const {
    today,
    month,
    todayPoints,
    monthPoints,
  } = useSalespersonMetrics(user?.id, { enabled: !!user });
  const [deltaTodayPoints, setDeltaTodayPoints] = useState('');
  const [deltaMonthPoints, setDeltaMonthPoints] = useState('');
  const [deltaAvgToday, setDeltaAvgToday] = useState('');
  const [deltaAvgMonth, setDeltaAvgMonth] = useState('');
  const [mujPlan, setMujPlan] = useState(null);
  const [mujPlanLoading, setMujPlanLoading] = useState(true);
  const [mujPlanError, setMujPlanError] = useState(null);
  const [mujPlanMesic, setMujPlanMesic] = useState(null); // {rok, mesic} pro dropdown
  const [mujPlanView, setMujPlanView] = useState('denni'); // 'denni' | 'mesicni' – výchozí denní
  const [news, setNews] = useState([]);
  const [upcoming, setUpcoming] = useState([]);

  useEffect(() => {
    if (today?.compare) setDeltaAvgToday(fmtDelta(today.compare.delta_avg));
  }, [today]);

  useEffect(() => {
    if (month?.compare) setDeltaAvgMonth(fmtDelta(month.compare.delta_avg));
  }, [month]);

  useEffect(() => {
    setDeltaTodayPoints(fmtDelta(todayPoints?.compare?.delta_points, ' b.'));
  }, [todayPoints]);

  useEffect(() => {
    setDeltaMonthPoints(fmtDelta(monthPoints?.compare?.delta_points, ' b.'));
  }, [monthPoints]);

  useEffect(() => {
    if (!user) return;
    loadMujPlan();
    loadNews();
    loadUpcoming();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user]);

  const loadMujPlan = async (rok, mesic) => {
    setMujPlanLoading(true);
    setMujPlanError(null);
    try {
      const today = new Date();
      const r = rok ?? today.getFullYear();
      const m = mesic ?? today.getMonth() + 1;
      const data = await plansAPI.getMujPlan(r, m);
      setMujPlan(data);
      setMujPlanMesic({ rok: r, mesic: m });
    } catch (err) {
      setMujPlanError(err.message || 'Chyba při načítání plánu');
      setMujPlan(null);
    } finally {
      setMujPlanLoading(false);
    }
  };

  const loadNews = async () => {
    try {
      const data = await newsAPI.list();
      setNews((data || []).slice(0, 5));
    } catch {
      /* tiché */
    }
  };

  const loadUpcoming = async () => {
    const today = new Date();
    const ym = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}`;
    try {
      const data = await shiftsAPI.listByMonth(ym);
      const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;
      const future = (data || [])
        .filter((s) => s.datum >= todayStr)
        .sort((a, b) => (a.datum < b.datum ? -1 : a.datum > b.datum ? 1 : (a.cas_od || '').localeCompare(b.cas_od || '')))
        .slice(0, 3);
      setUpcoming(future);
    } catch {
      /* tiché */
    }
  };

  const pointsTodayVal = number(todayPoints?.total_points || 0);
  const pointsMonthVal = number(monthPoints?.total_points || 0);
  const avgToday = number(today?.prumer_polozek_uctu ?? today?.pol_dok ?? 0);
  const avgMonth = number(month?.prumer_polozek_uctu ?? month?.pol_dok ?? 0);

  const roleLabel = user?.role === 'VEDOUCI' ? 'Vedoucí'
    : user?.role === 'BRIGADNIK' ? 'Brigádník'
    : user?.role === 'ADMIN' ? 'Administrátor'
    : 'Prodejce';

  const monthSelectOptions = useMemo(() => {
    const opts = [];
    const ref = new Date();
    for (let i = -2; i <= 2; i++) {
      const d = new Date(ref.getFullYear(), ref.getMonth() + i, 1);
      const rok = d.getFullYear();
      const mesic = d.getMonth() + 1;
      opts.push({
        value: `${rok}-${mesic}`,
        label: d.toLocaleDateString('cs-CZ', { month: 'long', year: 'numeric' }),
      });
    }
    return opts;
  }, []);

  const monthSelectValue = mujPlanMesic
    ? `${mujPlanMesic.rok}-${mujPlanMesic.mesic}`
    : `${new Date().getFullYear()}-${new Date().getMonth() + 1}`;

  return (
    <div className="seller-dashboard">
      <PageHeader
        title={`Vítej zpět, ${user?.jmeno || ''}`}
        subtitle={`${roleLabel} · Dnes je ${new Date().toLocaleDateString('cs-CZ')}`}
        actions={(
          <>
            <button
              type="button"
              className="btn btn--secondary"
              onClick={() => navigate('/tasks')}
            >
              Úkoly
            </button>
            <button type="button" className="btn btn--primary" onClick={() => navigate('/shifts')}>
              Plán směn
            </button>
          </>
        )}
      />

      <DashboardModuleHub />

      <div className="seller-metrics">
        <MetricCard title="Dnešní skóre" value={`${pointsTodayVal} b.`} delta={deltaTodayPoints} sub={todayPoints?.source && `zdroj: ${todayPoints.source}`} />
        <MetricCard title="Měsíc zatím" value={`${pointsMonthVal} b.`} delta={deltaMonthPoints} sub={monthPoints?.source && `zdroj: ${monthPoints.source}`} />
        <MetricCard title="Průměr položek na účtenku dnes" value={avgToday} delta={deltaAvgToday} />
        <MetricCard title="Průměr položek na účtenku měsíc" value={avgMonth} delta={deltaAvgMonth} />
      </div>

      <div className="content-grid">
        <div className="left-col">
          <div className="card muj-plan-card">
            <div className="muj-plan-header">
              <h3 className="chart-title big">Můj plán</h3>
              <div className="muj-plan-header-right">
                <SegmentControl
                  options={[
                    { id: 'denni', label: 'Denní' },
                    { id: 'mesicni', label: 'Měsíční' },
                  ]}
                  value={mujPlanView}
                  onChange={setMujPlanView}
                  expanded={false}
                  ariaLabel="Zobrazení plánu"
                  className="muj-plan-segment"
                />
                <Select
                  className="muj-plan-select"
                  options={monthSelectOptions}
                  value={monthSelectValue}
                  onChange={(v) => {
                    const [r, m] = v.split('-').map(Number);
                    loadMujPlan(r, m);
                  }}
                  aria-label="Měsíc plánu"
                />
              </div>
            </div>

            {mujPlanLoading && <div className="muj-plan-loading">Načítám plán…</div>}
            {mujPlanError && <div className="muj-plan-error">{mujPlanError}</div>}

            {!mujPlanLoading && !mujPlanError && mujPlan && (
              <>
                {mujPlan.celkem_polozek === 0 ? (
                  <div className="muj-plan-empty">Pro tento měsíc nemáte přidělený plán.</div>
                ) : (() => {
                  const PRUMER_PRACOVNICH_DNI = 19;
                  const pracovnichDni = mujPlan.pracovnich_dni ?? 0;
                  const smenDnes = mujPlan.smen_dnes ?? 0;
                  const jeDenni = mujPlanView === 'denni';
                  const divisor = jeDenni ? (pracovnichDni > 0 ? pracovnichDni : PRUMER_PRACOVNICH_DNI) : 1;
                  const showDenni = jeDenni;
                  const nemaSmeny = jeDenni && pracovnichDni === 0;
                  const celkemZobraz = showDenni ? Math.ceil(mujPlan.celkem_polozek / divisor) : mujPlan.celkem_polozek;
                  const formatKs = (val) => number(Math.round(val));
                  return (
                    <>
                      {nemaSmeny && (
                        <div className="muj-plan-info muj-plan-info-warning">Zobrazuje se odhadovaný průměr, pro přesné číslo si doplň směny!</div>
                      )}
                      <div className="muj-plan-total">
                        Celkem <strong>{formatKs(celkemZobraz)}</strong> položek {showDenni ? 'za den' : 'za měsíc'}
                        {mujPlan.plneni && (() => {
                          const skutecneTotal = showDenni ? (mujPlan.plneni.celkem_dnes ?? 0) : mujPlan.plneni.celkem_skutecne;
                          const cilTotal = showDenni ? celkemZobraz : mujPlan.celkem_polozek;
                          const pctTotal = cilTotal > 0 ? Math.min(100, (skutecneTotal / cilTotal) * 100) : 0;
                          return (
                            <span className="muj-plan-plneni-meta">
                              {' '}· splněno <strong>{skutecneTotal}</strong> / {showDenni ? formatKs(cilTotal) : cilTotal} ks{' '}
                              <span className={`muj-plan-pct-badge ${pctTotal >= 100 ? 'muj-plan-trend-ok' : pctTotal >= 80 ? 'muj-plan-trend-var' : 'muj-plan-trend-chyba'}`}>
                                {pctTotal.toFixed(1)} %
                              </span>
                              {!showDenni && mujPlan.plneni.trend_procent != null && (
                                <span className={`muj-plan-trend-badge ${trendTrida(mujPlan.plneni.trend_procent)}`}>
                                  → ~{mujPlan.plneni.trend_kusy} ks
                                </span>
                              )}
                            </span>
                          );
                        })()}
                        {!showDenni && mujPlan.celkem_castka && parseFloat(mujPlan.celkem_castka) > 0 && ` · ${number(parseFloat(mujPlan.celkem_castka))} Kč`}
                        {showDenni && (pracovnichDni > 0 ? (
                          <span className="muj-plan-meta"> ({pracovnichDni} prac. dní)</span>
                        ) : nemaSmeny ? null : (
                          <span className="muj-plan-meta"> (odhad /19)</span>
                        ))}
                      </div>
                      <div className="muj-plan-bars">
                        {(mujPlan.kategorie || []).filter(k => k.pocet_kusu > 0).map((k) => {
                          const cil = showDenni ? Math.ceil(k.pocet_kusu / divisor) : k.pocet_kusu;
                          const skutecne = showDenni ? (k.skutecne_dnes ?? 0) : (k.skutecne_kusy ?? 0);
                          const pct = cil > 0 ? Math.min(100, (skutecne / cil) * 100) : 0;
                          return (
                            <div key={k.kategorie_kod} className="muj-plan-bar-item">
                              <div className="muj-plan-bar-header">
                                <span
                                  className="muj-plan-bar-name"
                                  title={k.napoveda || undefined}
                                >
                                  {k.kategorie_nazev}
                                </span>
                                <span className="muj-plan-bar-count">
                                  {skutecne} / {formatKs(cil)} ks{' '}
                                  <span className={`muj-plan-pct-badge ${pct >= 100 ? 'muj-plan-trend-ok' : pct >= 80 ? 'muj-plan-trend-var' : 'muj-plan-trend-chyba'}`}>
                                    {pct.toFixed(1)} %
                                  </span>
                                  {!showDenni && k.trend_kusy != null && (
                                    <span className={`muj-plan-trend-badge ${trendTrida(k.trend_procent)}`}>
                                      → ~{k.trend_kusy} ks
                                    </span>
                                  )}
                                </span>
                              </div>
                              <div className="muj-plan-bar-track">
                                <div
                                  className="muj-plan-bar-fill"
                                  style={{ width: `${Math.min(100, pct)}%` }}
                                  title={`${skutecne} / ${formatKs(cil)} ks (${pct.toFixed(1)} %)`}
                                />
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </>
                  );
                })()}
              </>
            )}
          </div>

          <div className="below-cards">
            <div className="card">
              <h3>Novinky</h3>
              <div className="news-list">
                {news.map((n) => (
                  <Link key={n.id} to={`/news#post-${n.id}`} className="news-item news-item-link">
                    <div style={{ display: 'flex', gap: 8, alignItems: 'center', minWidth: 0 }}>
                      <span>📰</span>
                      <div style={{ fontWeight: 600, maxWidth: 210, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {n.obsah}
                      </div>
                    </div>
                    <div className="metric-sub">{formatNewsAge(n.datum_vytvoreni)}</div>
                  </Link>
                ))}
              </div>
            </div>
          </div>
        </div>
        <div className="right-col">
          <div className="card" style={{marginBottom: 16}}>
            <h3>Dnešní směna</h3>
            <AttendancePanel user={user} />
          </div>
          <div className="card" style={{marginBottom: 16}}>
            <h3>Nejbližší směny</h3>
            <div className="news-list">
              {upcoming.map((s) => (
                <div key={s.id} className="news-item">
                  <div>
                    <strong>{new Date(s.datum).toLocaleDateString('cs-CZ', { weekday: 'short' })}</strong>
                    &nbsp;{new Date(s.datum).toLocaleDateString('cs-CZ')} · {(s.cas_od || '').substring(0,5)}–{(s.cas_do || '').substring(0,5)}
                  </div>
                  <div className="metric-sub">{s.prodejna || s.prodejna_nazev}</div>
                </div>
              ))}
              {!upcoming.length && <div className="metric-sub">Žádné nadcházející směny</div>}
            </div>
          </div>
        </div>
      </div>

      
    </div>
  );
}


