import React, { useEffect, useState } from 'react';
import { plansAPI } from '../../services/api';

export default function AuditZbytekPanel({ rok, mesic }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!rok || !mesic) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    plansAPI.getAuditZbytek(rok, mesic)
      .then((res) => { if (!cancelled) setData(res); })
      .catch((e) => { if (!cancelled) setError(e?.message || 'Chyba načítání'); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [rok, mesic]);

  if (loading) return <div className="audit-zbytek-loading">Načítám audit Zbytku…</div>;
  if (error) return <div className="audit-zbytek-error">{error}</div>;
  if (!data) return null;

  const rows = data.radky || [];
  if (!rows.length && !data.celkem_zbytek_kusy) return null;

  return (
    <section className="audit-zbytek-panel">
      <h3 className="audit-zbytek-title">Audit Zbytku (admin)</h3>
      <p className="audit-zbytek-meta">
        Celkem ve Zbytku: <strong>{data.celkem_zbytek_kusy}</strong> ks
        {data.pracovni_podil_procent > 0 && (
          <> · pracovní kategorie: <strong>{data.pracovni_podil_procent} %</strong> ({data.pracovni_kusy} ks)</>
        )}
      </p>
      {rows.length > 0 && (
        <table className="audit-zbytek-table">
          <thead>
            <tr>
              <th>Symplio kategorie</th>
              <th>Podkategorie</th>
              <th>Ks</th>
              <th>Obrat bez DPH</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i} className={r.je_pracovni ? 'audit-zbytek-pracovni' : ''}>
                <td>{r.kategorie}</td>
                <td>{r.kategorie_1 || '—'}</td>
                <td>{r.kusy}</td>
                <td>{Number(r.obrat_bez_dph || 0).toLocaleString('cs-CZ')} Kč</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <p className="audit-zbytek-hint">
        Zvýrazněné řádky jsou pracovní záložky (Nově naskladněno, Zakládání, …) – cíl je je postupně přeřadit ve Symplio.
      </p>
    </section>
  );
}
