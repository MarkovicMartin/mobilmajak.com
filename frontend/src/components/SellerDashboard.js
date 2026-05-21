import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getApiEndpoints } from '../config/apiConfig';
import { AnalyticsDateInput } from './AnalyticsDateRange';
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
  const endpoints = useMemo(() => getApiEndpoints(), []);
  const [today, setToday] = useState(null);
  const [month, setMonth] = useState(null);
  const [todayPoints, setTodayPoints] = useState(null);
  const [monthPoints, setMonthPoints] = useState(null);
  const [deltaTodayPoints, setDeltaTodayPoints] = useState('');
  const [deltaMonthPoints, setDeltaMonthPoints] = useState('');
  const [deltaAvgToday, setDeltaAvgToday] = useState('');
  const [deltaAvgMonth, setDeltaAvgMonth] = useState('');
  const [mujPlan, setMujPlan] = useState(null);
  const [mujPlanLoading, setMujPlanLoading] = useState(true);
  const [mujPlanError, setMujPlanError] = useState(null);
  const [mujPlanMesic, setMujPlanMesic] = useState(null); // {rok, mesic} pro dropdown
  const [mujPlanView, setMujPlanView] = useState('denni'); // 'denni' | 'mesicni' – výchozí denní
  const [tasks, setTasks] = useState([]);
  const [newTask, setNewTask] = useState({ ukol: '', priorita: 'stredni', deadline: '' });
  const [news, setNews] = useState([]);
  const [upcoming, setUpcoming] = useState([]);

  useEffect(() => {
    if (!user) return;
    const uid = user.id;
    fetch(`${endpoints.salespersonToday}?user_id=${uid}`, { credentials: 'include' })
      .then((r) => r.json()).then((d)=>{ setToday(d); if (d?.compare) setDeltaAvgToday(fmtDelta(d.compare.delta_avg)); }).catch(() => {});
    fetch(`${endpoints.salespersonMonthly}?user_id=${uid}`, { credentials: 'include' })
      .then((r) => r.json()).then((d)=>{ setMonth(d); if (d?.compare) setDeltaAvgMonth(fmtDelta(d.compare.delta_avg)); }).catch(() => {});
    fetch(`${endpoints.salespersonPointsToday}?user_id=${uid}`, { credentials: 'include' })
      .then((r) => r.json()).then((d)=>{ setTodayPoints(d); setDeltaTodayPoints(fmtDelta(d?.compare?.delta_points,' b.'));}).catch(() => {});
    fetch(`${endpoints.salespersonPointsMonthly}?user_id=${uid}`, { credentials: 'include' })
      .then((r) => r.json()).then((d)=>{ setMonthPoints(d); setDeltaMonthPoints(fmtDelta(d?.compare?.delta_points,' b.'));}).catch(() => {});

    loadMujPlan();
    loadTasks();
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
      const res = await fetch(`/api/plans/muj-plan/?rok=${r}&mesic=${m}`, { credentials: 'include' });
      if (!res.ok) throw new Error('Nepodařilo se načíst plán');
      const data = await res.json();
      setMujPlan(data);
      setMujPlanMesic({ rok: r, mesic: m });
    } catch (err) {
      setMujPlanError(err.message || 'Chyba při načítání plánu');
      setMujPlan(null);
    } finally {
      setMujPlanLoading(false);
    }
  };

  const loadTasks = async (stav = 'vse') => {
    const res = await fetch(`/api/tasks/?stav=${stav}`, { credentials: 'include' });
    if (res.ok) setTasks(await res.json());
  };

  const createTask = async () => {
    if (!newTask.ukol) return;
    const res = await fetch('/api/tasks/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({
        ukol: newTask.ukol,
        priorita: newTask.priorita,
        deadline: newTask.deadline || null,
      }),
    });
    if (res.ok) {
      setNewTask({ ukol: '', priorita: 'stredni', deadline: '' });
      loadTasks('vse');
    }
  };

  const toggleDone = async (task) => {
    const res = await fetch(`/api/tasks/${task.id}/`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ stav: task.stav === 'hotovo' ? 'v_procesu' : 'hotovo' }),
    });
    if (res.ok) loadTasks('vse');
  };

  const loadNews = async () => {
    const res = await fetch('/api/news/', { credentials: 'include' });
    if (res.ok) {
      const data = await res.json();
      setNews((data || []).slice(0, 5));
    }
  };

  const loadUpcoming = async () => {
    const today = new Date();
    const ym = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}`;
    const res = await fetch(`/api/shifts/?mesic=${ym}`, { credentials: 'include' });
    if (!res.ok) return;
    const data = await res.json();
    const todayStr = today.toISOString().split('T')[0];
    const future = (data || [])
      .filter((s) => s.datum >= todayStr)
      .sort((a, b) => (a.datum < b.datum ? -1 : a.datum > b.datum ? 1 : (a.cas_od || '').localeCompare(b.cas_od || '')))
      .slice(0, 3);
    setUpcoming(future);
  };

  const pointsTodayVal = number(todayPoints?.total_points || 0);
  const pointsMonthVal = number(monthPoints?.total_points || 0);
  const avgToday = number(today?.prumer_polozek_uctu ?? today?.pol_dok ?? 0);
  const avgMonth = number(month?.prumer_polozek_uctu ?? month?.pol_dok ?? 0);

  return (
    <div className="seller-dashboard">
      <div className="seller-head">
        <div>
          <div className="seller-head-title">Vítej zpět, {user?.jmeno} 👋</div>
          <div className="seller-head-sub">Role: {user?.role === 'VEDOUCI' ? 'Vedoucí' : 'Prodejce'} • Dnes je {new Date().toLocaleDateString('cs-CZ')}</div>
        </div>
        <div className="seller-head-actions">
          <button className="btn-rounded" onClick={() => navigate('/shifts')}>Plán směn</button>
        </div>
      </div>

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
                <div className="pill-toggle">
                  <button
                    className={mujPlanView === 'denni' ? 'active' : ''}
                    onClick={() => setMujPlanView('denni')}
                  >
                    Denní
                  </button>
                  <button
                    className={mujPlanView === 'mesicni' ? 'active' : ''}
                    onClick={() => setMujPlanView('mesicni')}
                  >
                    Měsíční
                  </button>
                </div>
                <select
                className="muj-plan-select"
                value={mujPlanMesic ? `${mujPlanMesic.rok}-${mujPlanMesic.mesic}` : `${new Date().getFullYear()}-${new Date().getMonth() + 1}`}
                onChange={(e) => {
                  const [r, m] = e.target.value.split('-').map(Number);
                  loadMujPlan(r, m);
                }}
              >
                {(() => {
                  const opts = [];
                  const today = new Date();
                  for (let i = -2; i <= 2; i++) {
                    const d = new Date(today.getFullYear(), today.getMonth() + i, 1);
                    const rok = d.getFullYear();
                    const mesic = d.getMonth() + 1;
                    opts.push(
                      <option key={`${rok}-${mesic}`} value={`${rok}-${mesic}`}>
                        {d.toLocaleDateString('cs-CZ', { month: 'long', year: 'numeric' })}
                      </option>
                    );
                  }
                  return opts;
                })()}
                </select>
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
                                <span className="muj-plan-bar-name">{k.kategorie_nazev}</span>
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

          {/* Novinky + Úkoly přímo pod grafem v levém sloupci */}
          <div className="below-cards">
            <div className="card">
              <h3>Úkoly od vedoucího</h3>
              <div className="tasks-header">
                <div style={{display:'flex', gap:8}}>
                  <button onClick={() => loadTasks('vse')}>Aktuální</button>
                  <button onClick={() => loadTasks('hotovo')}>Hotové</button>
                </div>
              </div>
              <div style={{display:'grid', gap:8, marginTop:12}}>
                <input placeholder="Úkol" value={newTask.ukol} onChange={(e)=>setNewTask({...newTask, ukol:e.target.value})} />
                <select value={newTask.priorita} onChange={(e)=>setNewTask({...newTask, priorita:e.target.value})}>
                  <option value="nizka">Nízká</option>
                  <option value="stredni">Střední</option>
                  <option value="vysoka">Vysoká</option>
                </select>
                <AnalyticsDateInput
                  value={newTask.deadline}
                  onApply={(deadline) => setNewTask(prev => ({ ...prev, deadline }))}
                  showError={false}
                />
                <button onClick={createTask}>Přidat úkol</button>
              </div>
              <div className="tasks-list">
                {tasks.map((t)=> (
                  <div key={t.id} className="task-item">
                    <div className="task-left">
                      <input type="checkbox" checked={t.stav==='hotovo'} onChange={()=>toggleDone(t)} />
                      <div>
                        <div className="task-title">{t.ukol}</div>
                        <div className="metric-sub">Priorita: {t.priorita} {t.deadline && `· do ${new Date(t.deadline).toLocaleDateString('cs-CZ')}`}</div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
            <div className="card">
              <h3>Novinky</h3>
              <div className="news-list">
                {news.map((n)=> (
                  <div key={n.id} className="news-item">
                    <div style={{display:'flex', gap:8, alignItems:'center'}}>
                      <span>📰</span>
                      <div style={{fontWeight:600, maxWidth:210, overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap'}}>
                        {n.obsah}
                      </div>
                    </div>
                    <div className="metric-sub">před {Math.max(1, Math.round((Date.now() - new Date(n.datum_vytvoreni)) / 36e5))} h</div>
                  </div>
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


