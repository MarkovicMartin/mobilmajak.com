import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';

export default function PlanProdejcuPanel({ planProdejnaId }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [chyba, setChyba] = useState(null);
  const [uspech, setUspech] = useState(null);

  // Formulář pro přidání/úpravu prodejce
  const [vybranyProdejce, setVybranyProdejce] = useState(null); // { id, jmeno, prijmeni }
  const [formKusy, setFormKusy] = useState({}); // { kategorie_kod: pocet }
  const [editujProdejceId, setEditujProdejceId] = useState(null); // při úpravě existujícího
  const [pridatPodleSmenLoading, setPridatPodleSmenLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setChyba(null);
    try {
      const res = await axios.get(`/api/plans/prodejna/${planProdejnaId}/prodejci/`);
      setData(res.data);
    } catch {
      setChyba('Nepodařilo se načíst plán prodejců.');
    } finally {
      setLoading(false);
    }
  }, [planProdejnaId]);

  useEffect(() => { load(); }, [load]);

  const pridaniProdejci = data?.prodejci_domovska || [];
  const ostatniProdejci = data?.prodejci_ostatni || [];
  const pridaniIds = new Set((data?.plany_prodejcu || []).map(pp => pp.uzivatel_id));
  const dostupniProdejci = [
    ...pridaniProdejci.filter(u => !pridaniIds.has(u.id)),
    ...ostatniProdejci.filter(u => !pridaniIds.has(u.id)),
  ];

  const aktivniKategorie = (data?.kategorie_prodejny || []).filter(
    k => k.pocet_kusu_plan != null && k.pocet_kusu_plan > 0
  );

  const onFormKusChange = (kod, val) => {
    const num = val === '' ? 0 : Math.max(0, parseInt(val, 10) || 0);
    setFormKusy(prev => ({ ...prev, [kod]: num }));
  };

  const pridatProdejce = async () => {
    if (!vybranyProdejce && !editujProdejceId) return;

    const uzivatelId = editujProdejceId ?? vybranyProdejce.id;
    const kategorie = {};
    for (const k of aktivniKategorie) {
      const v = formKusy[k.kategorie_kod] ?? 0;
      if (v > 0) kategorie[k.kategorie_kod] = { pocet_kusu: v, castka: 0 };
    }

    const existujici = (data?.plany_prodejcu || []).filter(pp => pp.uzivatel_id !== uzivatelId);
    const novy = { uzivatel_id: uzivatelId, kategorie };
    const prodejci = [...existujici.map(pp => ({
      uzivatel_id: pp.uzivatel_id,
      kategorie: pp.kategorie,
    })), novy].map(p => ({
      uzivatel_id: p.uzivatel_id,
      kategorie: Object.fromEntries(
        Object.entries(p.kategorie || {}).map(([kod, val]) => [
          kod,
          { pocet_kusu: typeof val === 'object' ? val.pocet_kusu : val, castka: 0 },
        ])
      ),
    }));

    setSaving(true);
    setChyba(null);
    setUspech(null);
    try {
      const res = await axios.post(`/api/plans/prodejna/${planProdejnaId}/prodejci/ulozit/`, { prodejci });
      setData(prev => ({ ...prev, ...res.data }));
      setUspech(editujProdejceId ? 'Plán prodejce upraven.' : 'Prodejce přidán.');
      setVybranyProdejce(null);
      setFormKusy({});
      setEditujProdejceId(null);
    } catch {
      setChyba('Nepodařilo se uložit.');
    } finally {
      setSaving(false);
    }
  };

  const odebratProdejce = async (uzivatelId) => {
    const prodejci = (data?.plany_prodejcu || [])
      .filter(pp => pp.uzivatel_id !== uzivatelId)
      .map(pp => ({
        uzivatel_id: pp.uzivatel_id,
        kategorie: Object.fromEntries(
          Object.entries(pp.kategorie || {}).map(([kod, val]) => [
            kod,
            { pocet_kusu: typeof val === 'object' ? val.pocet_kusu : val, castka: 0 },
          ])
        ),
      }));

    setSaving(true);
    setChyba(null);
    setUspech(null);
    try {
      const res = await axios.post(`/api/plans/prodejna/${planProdejnaId}/prodejci/ulozit/`, { prodejci });
      setData(prev => ({ ...prev, ...res.data }));
      setUspech('Prodejce odebrán.');
      if (editujProdejceId === uzivatelId) {
        setEditujProdejceId(null);
        setVybranyProdejce(null);
        setFormKusy({});
      }
    } catch {
      setChyba('Nepodařilo se odebrat.');
    } finally {
      setSaving(false);
    }
  };

  const zacitUpravit = (pp) => {
    setEditujProdejceId(pp.uzivatel_id);
    setVybranyProdejce(null);
    const kusy = {};
    for (const [kod, val] of Object.entries(pp.kategorie || {})) {
      kusy[kod] = val.pocet_kusu ?? 0;
    }
    setFormKusy(kusy);
  };

  const zrusitFormular = () => {
    setVybranyProdejce(null);
    setFormKusy({});
    setEditujProdejceId(null);
  };

  const pridatPodleSmen = async () => {
    const uzivatelId = editujProdejceId ?? vybranyProdejce?.id;
    if (!uzivatelId || !data?.prodejna_id || data?.rok == null || data?.mesic == null) return;

    setPridatPodleSmenLoading(true);
    setChyba(null);
    try {
      const mesicStr = `${data.rok}-${String(data.mesic).padStart(2, '0')}`;
      const res = await axios.get('/api/shifts/count/', {
        params: { user_id: uzivatelId, prodejna_id: data.prodejna_id, mesic: mesicStr },
      });
      const pocetSmen = res.data.pocet_smen ?? 0;

      if (pocetSmen === 0) {
        setChyba('Prodejce nemá nastavené směny');
        return;
      }

      const dni = new Date(data.rok, data.mesic, 0).getDate();
      const noveKusy = {};
      for (const k of aktivniKategorie) {
        const plan = k.pocet_kusu_plan || 0;
        const val = Math.ceil((plan / dni) * pocetSmen);
        noveKusy[k.kategorie_kod] = val;
      }
      setFormKusy(prev => ({ ...prev, ...noveKusy }));
    } catch {
      setChyba('Nepodařilo se načíst počet směn.');
    } finally {
      setPridatPodleSmenLoading(false);
    }
  };

  if (loading) return <div className="pp-loading">Načítám plán prodejců…</div>;
  if (!data) return null;

  const { kategorie_prodejny, plany_prodejcu, prideleno_kusu } = data;
  const maFormular = vybranyProdejce || editujProdejceId;
  const editovanyProdejce = editujProdejceId
    ? plany_prodejcu.find(pp => pp.uzivatel_id === editujProdejceId)
    : null;

  return (
    <div className="pp-panel">
      <div className="pp-panel-header">
        <span className="pp-panel-title">👥 Plán prodejců</span>
      </div>

      {chyba && <div className="plans-alert plans-alert-error">{chyba}</div>}
      {uspech && <div className="plans-alert plans-alert-success">{uspech}</div>}

      {/* Souhrn plánu prodejny */}
      {aktivniKategorie.length > 0 && (
        <div className="pp-souhrn">
          {aktivniKategorie.map(k => {
            const prideleno = prideleno_kusu[k.kategorie_kod] || 0;
            const plan = k.pocet_kusu_plan;
            const zbyvaPct = plan > 0 ? Math.max(0, Math.round((1 - prideleno / plan) * 100)) : 0;
            const over = prideleno > plan;
            return (
              <div key={k.kategorie_kod} className={`pp-souhrn-item${over ? ' pp-over' : ''}`}>
                <span className="pp-souhrn-nazev">{k.kategorie_nazev}</span>
                <span className="pp-souhrn-plan">plán {plan} ks</span>
                <div className="pp-souhrn-bar-wrap">
                  <div
                    className="pp-souhrn-bar"
                    style={{ width: `${Math.min(100, plan > 0 ? (prideleno / plan) * 100 : 0)}%`, background: over ? '#ef4444' : '#6d28d9' }}
                  />
                </div>
                <span className={over ? 'pp-over-text' : 'pp-souhrn-zbývá'}>
                  {over ? `+${prideleno - plan} ks nad plán` : `zbývá ${plan - prideleno} ks (${zbyvaPct} %)`}
                </span>
              </div>
            );
          })}
        </div>
      )}

      {/* Formulář přidání prodejce */}
      {aktivniKategorie.length > 0 && (
        <div className="pp-form-wrap">
          <div className="pp-form-header">➕ Přidat prodejce</div>
          <div className="pp-form-row">
            <label className="pp-form-label">Prodejce</label>
            <select
              className="pp-select"
              value={vybranyProdejce ? vybranyProdejce.id : ''}
              onChange={e => {
                const id = e.target.value ? Number(e.target.value) : null;
                if (id) {
                  const u = dostupniProdejci.find(x => x.id === id) || pridaniProdejci.find(x => x.id === id) || ostatniProdejci.find(x => x.id === id);
                  if (u) {
                    setVybranyProdejce(u);
                    setEditujProdejceId(null);
                    setFormKusy({});
                  }
                } else {
                  setVybranyProdejce(null);
                  setFormKusy({});
                }
              }}
              disabled={!!editujProdejceId}
            >
              <option value="">— vyberte prodejce —</option>
              {pridaniProdejci.filter(u => !pridaniIds.has(u.id)).length > 0 && (
                <optgroup label="Prodejci této prodejny">
                  {pridaniProdejci.filter(u => !pridaniIds.has(u.id)).map(u => (
                    <option key={u.id} value={u.id}>{u.jmeno} {u.prijmeni}</option>
                  ))}
                </optgroup>
              )}
              {ostatniProdejci.filter(u => !pridaniIds.has(u.id)).length > 0 && (
                <optgroup label="Ostatní prodejci">
                  {ostatniProdejci.filter(u => !pridaniIds.has(u.id)).map(u => (
                    <option key={u.id} value={u.id}>{u.jmeno} {u.prijmeni}</option>
                  ))}
                </optgroup>
              )}
              {dostupniProdejci.length === 0 && (
                <option value="" disabled>Všichni prodejci již přidáni</option>
              )}
            </select>
          </div>

          {maFormular && (
            <>
              <div className="pp-form-vybrany">
                {editujProdejceId
                  ? `Upravujete: ${editovanyProdejce?.jmeno} ${editovanyProdejce?.prijmeni}`
                  : `Vybráno: ${vybranyProdejce?.jmeno} ${vybranyProdejce?.prijmeni}`}
              </div>
              <div className="pp-form-kusy-label">
                Plánované kusy po kategoriích
                <button
                  type="button"
                  className="plans-btn plans-btn-ghost plans-btn-xs pp-btn-pridělit pp-btn-podle-smen"
                  onClick={pridatPodleSmen}
                  disabled={saving || pridatPodleSmenLoading}
                >
                  {pridatPodleSmenLoading ? 'Načítám…' : 'Přidělit podle směn'}
                </button>
              </div>
              <table className="pp-form-tabulka">
                <thead>
                  <tr>
                    <th className="pp-form-th">Kategorie</th>
                    <th className="pp-form-th">Ks</th>
                    <th className="pp-form-th">Zbývá</th>
                    <th className="pp-form-th pp-form-th-akce"></th>
                  </tr>
                </thead>
                <tbody>
                  {aktivniKategorie.map(k => {
                    const plan = k.pocet_kusu_plan || 0;
                    const prideleno = prideleno_kusu[k.kategorie_kod] || 0;
                    const aktualniProdejce = editovanyProdejce?.kategorie?.[k.kategorie_kod]?.pocet_kusu ?? 0;
                    const zbyva = editujProdejceId
                      ? Math.max(0, plan - prideleno + aktualniProdejce)
                      : Math.max(0, plan - prideleno);
                    return (
                      <tr key={k.kategorie_kod} className="pp-form-radek">
                        <td className="pp-form-td-label">{k.kategorie_nazev}</td>
                        <td className="pp-form-td-input">
                          <input
                            type="number"
                            min="0"
                            step="1"
                            value={formKusy[k.kategorie_kod] ?? ''}
                            onChange={e => onFormKusChange(k.kategorie_kod, e.target.value)}
                            placeholder="0"
                            className="pp-input"
                          />
                          <span className="pp-form-kat-plan">ks</span>
                        </td>
                        <td className="pp-form-td-zbyva">
                          <span className={zbyva === 0 ? 'pp-zbyva-nula' : ''}>{zbyva} ks</span>
                        </td>
                        <td className="pp-form-td-btn">
                          <button
                            type="button"
                            className="plans-btn plans-btn-ghost plans-btn-xs pp-btn-pridělit"
                            onClick={() => onFormKusChange(k.kategorie_kod, Math.floor(zbyva / 2))}
                            disabled={saving || zbyva === 0}
                          >
                            Přidělit půlku
                          </button>
                          <button
                            type="button"
                            className="plans-btn plans-btn-ghost plans-btn-xs pp-btn-pridělit"
                            onClick={() => onFormKusChange(k.kategorie_kod, zbyva)}
                            disabled={saving || zbyva === 0}
                          >
                            Přidělit zbytek
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              <div className="pp-form-akce">
                <button
                  className="plans-btn plans-btn-primary plans-btn-sm"
                  onClick={pridatProdejce}
                  disabled={saving}
                >
                  {saving ? 'Ukládám…' : editujProdejceId ? 'Uložit změny' : 'Přidat prodejce'}
                </button>
                <button
                  className="plans-btn plans-btn-ghost plans-btn-sm"
                  onClick={zrusitFormular}
                  disabled={saving}
                >
                  Zrušit
                </button>
              </div>
            </>
          )}
        </div>
      )}

      {/* Seznam přidaných prodejců */}
      {plany_prodejcu.length > 0 ? (
        <div className="pp-seznam">
          <div className="pp-seznam-header">Přidaní prodejci</div>
          {plany_prodejcu.map(pp => (
            <div key={pp.uzivatel_id} className="pp-radek-karta">
              <div className="pp-radek-hlavicka">
                <span className="pp-radek-jmeno">{pp.jmeno} {pp.prijmeni}</span>
                <div className="pp-radek-akce">
                  <button
                    className="plans-btn plans-btn-ghost plans-btn-xs"
                    onClick={() => zacitUpravit(pp)}
                    disabled={saving}
                  >
                    Upravit
                  </button>
                  <button
                    className="plans-btn plans-btn-ghost plans-btn-xs pp-btn-odebrat"
                    onClick={() => odebratProdejce(pp.uzivatel_id)}
                    disabled={saving}
                  >
                    Odebrat
                  </button>
                </div>
              </div>
              <div className="pp-radek-kusy">
                {aktivniKategorie.map(k => {
                  const val = pp.kategorie?.[k.kategorie_kod]?.pocet_kusu ?? 0;
                  if (val === 0) return null;
                  return (
                    <span key={k.kategorie_kod} className="pp-radek-kat">
                      {k.kategorie_nazev}: <strong>{val} ks</strong>
                    </span>
                  );
                })}
              </div>
            </div>
          ))}
          {/* Součet */}
          <div className="pp-soucet-radek">
            <span className="pp-soucet-label">Součet přidělen:</span>
            {aktivniKategorie.map(k => {
              const sum = prideleno_kusu[k.kategorie_kod] || 0;
              const plan = k.pocet_kusu_plan;
              const over = sum > plan;
              return (
                <span key={k.kategorie_kod} className={`pp-soucet-val${over ? ' pp-over-text' : sum === plan ? ' pp-ok-text' : ''}`}>
                  {k.kategorie_nazev}: {sum} / {plan}
                </span>
              );
            })}
          </div>
        </div>
      ) : aktivniKategorie.length > 0 ? (
        <div className="pp-empty">
          Vyberte prodejce z rolovátka, vyplňte kusy a klikněte na „Přidat prodejce“.
        </div>
      ) : (
        <div className="pp-empty">
          Nejdříve nastavte průměrné ceny kategorií pro výpočet kusů.
        </div>
      )}
    </div>
  );
}
