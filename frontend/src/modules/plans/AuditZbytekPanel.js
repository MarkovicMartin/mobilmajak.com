import React, { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import Modal from '../../components/Modal';
import { plansAPI } from '../../services/api';

const SYMPLIO_ORDER_URL = (orderId) =>
  `https://www.mobilmajak.cz/admin/objednavky/objednavka-${orderId}`;

const rowKey = (r) => `${r.kategorie}\0${r.kategorie_1 || ''}`;

const csvEscape = (value) => {
  const s = String(value ?? '');
  if (/[",;\n]/.test(s)) return `"${s.replace(/"/g, '""')}"`;
  return s;
};

const downloadCsv = (filename, rows) => {
  const header = [
    'datum',
    'kategorie',
    'podkategorie',
    'kod',
    'nazev',
    'ks',
    'cena_ks_bez_dph',
    'obrat_bez_dph',
    'doklad',
    'objednavka',
    'prodejna',
    'prodejce',
    'id_prodejce',
  ];
  const lines = [
    header.join(';'),
    ...rows.map((p) => [
      p.datum,
      p.kategorie,
      p.kategorie_1,
      p.kod,
      p.nazev,
      p.pocet_kusu,
      p.cena_ks_bez_dph,
      p.obrat_bez_dph,
      p.doklad,
      p.objednavka,
      p.stredisko,
      p.prodejce,
      p.id_prodejce ?? '',
    ].map(csvEscape).join(';')),
  ];
  const blob = new Blob(['\ufeff' + lines.join('\n')], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
};

export default function AuditZbytekPanel({ rok, mesic }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const [detailOpen, setDetailOpen] = useState(false);
  const [detailRow, setDetailRow] = useState(null);
  const [detailItems, setDetailItems] = useState([]);
  const [detailTotal, setDetailTotal] = useState(0);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState('');
  const [exporting, setExporting] = useState(false);

  const mesicParam = rok && mesic
    ? `${rok}-${String(mesic).padStart(2, '0')}`
    : '';

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

  const fetchPolozky = useCallback(async (row, { limit = 500, offset = 0 } = {}) => {
    const res = await plansAPI.getAuditZbytekPolozky(rok, mesic, {
      kategorie: row.kategorie,
      kategorie_1: row.kategorie_1 || '',
      limit,
      offset,
    });
    return res;
  }, [rok, mesic]);

  const openDetail = async (row) => {
    setDetailRow(row);
    setDetailOpen(true);
    setDetailItems([]);
    setDetailTotal(0);
    setDetailError('');
    setDetailLoading(true);
    try {
      const res = await fetchPolozky(row);
      setDetailItems(res.polozky || []);
      setDetailTotal(res.total ?? 0);
    } catch (e) {
      setDetailError(e?.message || 'Chyba načítání položek');
    } finally {
      setDetailLoading(false);
    }
  };

  const closeDetail = () => {
    setDetailOpen(false);
    setDetailRow(null);
    setDetailItems([]);
    setDetailError('');
  };

  const handleExport = async () => {
    if (!detailRow) return;
    setExporting(true);
    setDetailError('');
    try {
      const res = await fetchPolozky(detailRow, { limit: 2000, offset: 0 });
      const all = (res.polozky || []).map((p) => ({
        ...p,
        kategorie: detailRow.kategorie,
        kategorie_1: detailRow.kategorie_1 || '',
      }));
      if (res.has_more) {
        setDetailError(`Export obsahuje max. 2000 položek z ${res.total ?? '?'}.`);
      }
      const safeKat = (detailRow.kategorie || 'zbytek').replace(/[^\w\d-]+/gi, '_').slice(0, 40);
      downloadCsv(`audit-zbytek_${rok}-${String(mesic).padStart(2, '0')}_${safeKat}.csv`, all);
    } catch (e) {
      setDetailError(e?.message || 'Export se nezdařil');
    } finally {
      setExporting(false);
    }
  };

  if (loading) return <div className="audit-zbytek-loading">Načítám audit Zbytku…</div>;
  if (error) return <div className="audit-zbytek-error">{error}</div>;
  if (!data) return null;

  const rows = data.radky || [];
  if (!rows.length && !data.celkem_zbytek_kusy) return null;

  const detailTitle = detailRow
    ? `${detailRow.kategorie}${detailRow.kategorie_1 ? ` · ${detailRow.kategorie_1}` : ''}`
    : '';

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
            {rows.map((r) => (
              <tr
                key={rowKey(r)}
                className={`audit-zbytek-row ${r.je_pracovni ? 'audit-zbytek-pracovni' : ''}`}
              >
                <td>
                  <button
                    type="button"
                    className="audit-zbytek-row-btn"
                    onClick={() => openDetail(r)}
                  >
                    {r.kategorie}
                  </button>
                </td>
                <td>{r.kategorie_1 || '—'}</td>
                <td>
                  <button
                    type="button"
                    className="audit-zbytek-row-btn audit-zbytek-row-btn--ks"
                    onClick={() => openDetail(r)}
                  >
                    {r.kusy}
                  </button>
                </td>
                <td>{Number(r.obrat_bez_dph || 0).toLocaleString('cs-CZ')} Kč</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <p className="audit-zbytek-hint">
        Klikněte na kategorii nebo počet ks pro detail položek. Zvýrazněné řádky jsou pracovní záložky
        (Nově naskladněno, Zakládání, …) – cíl je je postupně přeřadit ve Symplio.
      </p>

      {detailOpen && (
        <Modal
          title={`Položky ve Zbytku: ${detailTitle}`}
          size="lg"
          onClose={closeDetail}
          footer={(
            <div className="audit-zbytek-detail-footer">
              <span className="audit-zbytek-detail-count">
                {detailLoading
                  ? 'Načítám…'
                  : `Zobrazeno ${detailItems.length} z ${detailTotal} položek`}
              </span>
              <button
                type="button"
                className="audit-zbytek-export-btn"
                onClick={handleExport}
                disabled={detailLoading || exporting || !detailTotal}
              >
                {exporting ? 'Exportuji…' : '⬇ Export CSV'}
              </button>
            </div>
          )}
        >
          {detailLoading && <p className="audit-zbytek-detail-loading">Načítám položky…</p>}
          {detailError && <p className="audit-zbytek-error">{detailError}</p>}
          {!detailLoading && detailItems.length > 0 && (
            <div className="audit-zbytek-detail-wrap">
              <table className="audit-zbytek-detail-table">
                <thead>
                  <tr>
                    <th>Datum</th>
                    <th>Produkt</th>
                    <th>Ks</th>
                    <th>Obrat bez DPH</th>
                    <th>Prodejna</th>
                    <th>Prodejce</th>
                    <th>Odkazy</th>
                  </tr>
                </thead>
                <tbody>
                  {detailItems.map((p, idx) => (
                    <tr key={`${p.datum}-${p.doklad}-${p.kod}-${idx}`}>
                      <td>{p.datum || '—'}</td>
                      <td className="audit-zbytek-product">
                        {p.kod && <code className="audit-zbytek-kod">{p.kod}</code>}
                        <span>{p.nazev || '—'}</span>
                      </td>
                      <td>{p.pocet_kusu}</td>
                      <td>{Number(p.obrat_bez_dph || 0).toLocaleString('cs-CZ')} Kč</td>
                      <td>{p.stredisko || '—'}</td>
                      <td>
                        {p.id_prodejce && mesicParam ? (
                          <Link
                            to={`/coaching/seller/${p.id_prodejce}?mesic=${mesicParam}`}
                            className="audit-zbytek-link"
                            onClick={closeDetail}
                          >
                            {p.prodejce || `#${p.id_prodejce}`}
                          </Link>
                        ) : (
                          p.prodejce || '—'
                        )}
                      </td>
                      <td className="audit-zbytek-links">
                        {p.objednavka ? (
                          <a
                            href={SYMPLIO_ORDER_URL(p.objednavka)}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="audit-zbytek-link"
                          >
                            Obj. {p.objednavka}
                          </a>
                        ) : null}
                        {p.doklad ? (
                          <span className="audit-zbytek-doklad" title="Číslo dokladu / účtenky">
                            🧾 {p.doklad}
                          </span>
                        ) : null}
                        {!p.objednavka && !p.doklad && '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {!detailLoading && !detailError && detailItems.length === 0 && (
            <p className="audit-zbytek-detail-empty">Žádné položky v tomto řádku.</p>
          )}
        </Modal>
      )}
    </section>
  );
}
