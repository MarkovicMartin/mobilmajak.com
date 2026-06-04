import React, { useState, useCallback } from 'react';
import { plansAPI } from '../../services/api';

/**
 * Strom plnění: celkové % → kategorie → položky (lazy).
 * kategorie: [{ kategorie_kod, kategorie_nazev, plneni_procent, plan_kusy, skutecne_kusy, trend_kusy, trend_procent }]
 */
export default function PlneniStrom({
  rok,
  mesic,
  nadpis,
  metaExtra,
  celkemPct,
  celkemMeta,
  kategorie = [],
  prodejnaId = null,
  prodejceId = null,
  plneniFillClass,
  plneniBarWidthPct,
  trendTrida,
  defaultOpen = false,
  showCelkemBar = true,
}) {
  const [openKat, setOpenKat] = useState(() => (defaultOpen ? {} : {}));
  const [polozkyCache, setPolozkyCache] = useState({});
  const [loadingKat, setLoadingKat] = useState({});

  const toggleKat = useCallback(async (kod) => {
    const willOpen = !openKat[kod];
    setOpenKat(prev => ({ ...prev, [kod]: willOpen }));
    if (willOpen && !polozkyCache[kod]) {
      setLoadingKat(prev => ({ ...prev, [kod]: true }));
      try {
        const params = { kategorie_kod: kod };
        if (prodejnaId != null) params.prodejna_id = prodejnaId;
        if (prodejceId != null) params.prodejce_id = prodejceId;
        const res = await plansAPI.getPlneniPolozky(rok, mesic, params);
        setPolozkyCache(prev => ({ ...prev, [kod]: res.polozky || [] }));
      } catch {
        setPolozkyCache(prev => ({ ...prev, [kod]: [] }));
      } finally {
        setLoadingKat(prev => ({ ...prev, [kod]: false }));
      }
    }
  }, [openKat, polozkyCache, rok, mesic, prodejnaId, prodejceId]);

  const pct = celkemPct ?? 0;
  const showHeader = showCelkemBar && (nadpis || celkemPct != null || celkemMeta || metaExtra);

  return (
    <div className="plneni-strom">
      {showHeader && (
        <>
          <div className="plneni-strom-header">
            {nadpis && <span className="plneni-strom-nadpis">{nadpis}</span>}
            {metaExtra}
            {celkemPct != null && (
              <span className="plneni-pct-badge plneni-strom-pct">{pct} %</span>
            )}
          </div>
          {celkemMeta && <div className="plneni-strom-meta">{celkemMeta}</div>}
          {celkemPct != null && (
            <div className="plneni-bar-wrap plneni-bar-prodejna">
              <div className="plneni-progress-track">
                <div
                  className={plneniFillClass(pct)}
                  style={{ width: `${plneniBarWidthPct(pct)}%` }}
                />
              </div>
            </div>
          )}
        </>
      )}
      <div className="plneni-strom-kat-list">
        {kategorie.map(k => {
          const pctKat = k.plneni_procent ?? 0;
          const isOpen = openKat[k.kategorie_kod];
          const polozky = polozkyCache[k.kategorie_kod];
          return (
            <div key={k.kategorie_kod} className="plneni-strom-kat">
              <button
                type="button"
                className="plneni-strom-kat-toggle"
                onClick={() => toggleKat(k.kategorie_kod)}
                aria-expanded={isOpen}
              >
                <span className="plneni-strom-kat-arrow">{isOpen ? '▼' : '▶'}</span>
                <span>{k.kategorie_nazev || k.kategorie_kod}</span>
                <span className="plneni-bar-meta">
                  {k.skutecne_kusy ?? 0} / {k.plan_kusy ?? '—'} ks
                  <span className="plneni-pct-badge">{pctKat} %</span>
                  {k.trend_kusy != null && (
                    <span className={`plneni-trend-badge ${trendTrida(k.trend_procent)}`}>
                      → ~{k.trend_kusy} ks
                    </span>
                  )}
                </span>
              </button>
              <div className="plneni-progress-track plneni-strom-kat-bar">
                <div
                  className={plneniFillClass(pctKat)}
                  style={{ width: `${plneniBarWidthPct(pctKat)}%` }}
                />
              </div>
              {isOpen && (
                <div className="plneni-strom-polozky">
                  {loadingKat[k.kategorie_kod] && (
                    <div className="plneni-strom-polozky-loading">Načítám položky…</div>
                  )}
                  {!loadingKat[k.kategorie_kod] && polozky && polozky.length === 0 && (
                    <div className="plneni-strom-polozky-empty">Žádné položky v kategorii.</div>
                  )}
                  {!loadingKat[k.kategorie_kod] && polozky?.map(p => (
                    <div key={p.kod} className="plneni-strom-polozka">
                      <span className="plneni-strom-polozka-nazev">{p.nazev || p.kod}</span>
                      <span className="plneni-strom-polozka-meta">
                        {p.kusy} ks · {Number(p.obrat).toLocaleString('cs-CZ')} Kč
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export function PlneniHistorieMini({ historie }) {
  const mesice = historie?.mesice || [];
  const signaly = historie?.signaly || {};
  if (!mesice.length) return null;
  const barColor = (pct) => {
    if (pct == null) return '#94a3b8';
    if (pct >= 100) return '#16a34a';
    if (pct >= 85) return '#ca8a04';
    return '#dc2626';
  };
  return (
    <div className="plneni-historie-wrap">
      <div className="plneni-historie-mini" title="Plnění za poslední 3 měsíce">
        {mesice.map(m => (
          <div
            key={`${m.rok}-${m.mesic}`}
            className="plneni-historie-bar"
            style={{
              height: `${Math.min(100, Math.max(8, m.plneni_procent_kusy || 0))}%`,
              background: barColor(m.plneni_procent_kusy),
            }}
            title={`${m.mesic_nazev} ${m.rok}: ${m.plneni_procent_kusy ?? '—'} %`}
          />
        ))}
      </div>
      {signaly.systematicky_pod_planem && (
        <span className="plneni-signal plneni-signal-warn" title="Všechny 3 měsíce pod 85 %">⚠ Pod plánem</span>
      )}
      {(signaly.silne_kategorie || []).length > 0 && (
        <span className="plneni-signal plneni-signal-ok" title={`Silné: ${signaly.silne_kategorie.join(', ')}`}>✓</span>
      )}
      {(signaly.slabe_kategorie || []).length > 0 && (
        <span className="plneni-signal plneni-signal-warn" title={`Slabé: ${signaly.slabe_kategorie.join(', ')}`}>↓</span>
      )}
    </div>
  );
}
