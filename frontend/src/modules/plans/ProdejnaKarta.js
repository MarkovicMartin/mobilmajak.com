import React, { useState } from 'react';
import { castkaBezDphZCelkem } from '../../utils/dph';
import PlanProdejcuPanel from './PlanProdejcuPanel';
import DraftNumberInput from './DraftNumberInput';

const formatCastka = (v) =>
  Number(v).toLocaleString('cs-CZ', { minimumFractionDigits: 0, maximumFractionDigits: 0 }) + ' Kč';

const formatBezDphParenBadge = (castkaVal) => {
  const bez = castkaBezDphZCelkem(castkaVal);
  if (!bez) return null;
  return (
    <span className="plans-castka-bezdph"> ({formatCastka(bez)} bez DPH)</span>
  );
};

const KATEGORIE_NAZVY = {
  NOVE_TELEFONY: 'Telefony nové',
  BAZAROVE_TELEFONY: 'Telefony bazarové',
  PRISLUSENSTVI_SKLA: 'Příslušenství – Skla',
  PRISLUSENSTVI_OBALY: 'Příslušenství – Obaly',
  PRISLUSENSTVI_OSTATNI: 'Příslušenství – Ostatní',
  SLUZBY: 'Služby',
  SERVIS: 'Servis',
  OSTATNI: 'Ostatní',
};

/**
 * Tří-stavový segmented control pro lock_mode.
 * Hodnoty: 'none' (auto), 'pct' (zamčené procento), 'kc' (zamčená absolutní Kč).
 */
function LockSegmented({ value, onChange, size = 'md', showLabels = true, disabled = false, title }) {
  const cls = (m) => {
    const base = 'lock-seg lock-seg-' + m;
    return value === m ? `${base} lock-seg-${m}-active` : base;
  };
  const sizeCls = size === 'sm' ? 'lock-segmented-sm' : 'lock-segmented-md';
  return (
    <div
      className={`lock-segmented ${sizeCls}${disabled ? ' lock-segmented-disabled' : ''}`}
      title={title}
      role="group"
      aria-label="Režim zámku"
    >
      <button type="button" className={cls('none')} onClick={() => !disabled && onChange('none')} disabled={disabled} title="Auto-dopočet">
        🔓{showLabels ? ' Auto' : ''}
      </button>
      <button type="button" className={cls('pct')} onClick={() => !disabled && onChange('pct')} disabled={disabled} title="Zamčené procento">
        🔒{showLabels ? ' %' : ''}
      </button>
      <button type="button" className={cls('kc')} onClick={() => !disabled && onChange('kc')} disabled={disabled} title="Zamčená absolutní Kč">
        💰{showLabels ? ' Kč' : ''}
      </button>
    </div>
  );
}

export default function ProdejnaKarta({ prodejna, castkaFirma, ostatniProdejny = [], onZmena }) {
  const [rozbalene, setRozbalene] = useState(false);
  const [rozbaleneProdejci, setRozbaleneProdejci] = useState(false);

  const lockMode = prodejna.lock_mode || 'none';
  const servisLockMode = prodejna.servis_lock_mode || 'none';

  // Zdroj pravdy pro input hodnoty (to, co uživatel naposledy zadal / uložil v state)
  const podilInput = Number(prodejna.podil_procenta);
  const castkaInput = Number(prodejna.castka_prodejna);
  const castkaProdejInput = Number(prodejna.castka_prodej);
  const castkaServisInput = Number(prodejna.castka_servis);

  // Dopočtené hodnoty z backendu (pokud existují)
  const podilShow = prodejna.podil_procenta_dopocet != null ? Number(prodejna.podil_procenta_dopocet) : podilInput;
  const castkaShow = prodejna.castka_prodejna_dopocet != null ? Number(prodejna.castka_prodejna_dopocet) : castkaInput;
  const castkaProdejShow = prodejna.castka_prodej_dopocet != null ? Number(prodejna.castka_prodej_dopocet) : castkaProdejInput;
  const castkaServisShow = prodejna.castka_servis_dopocet != null ? Number(prodejna.castka_servis_dopocet) : castkaServisInput;

  const castkaRef = castkaShow > 0 ? castkaShow : castkaInput;

  // Dopočítané podíly pro slider/display
  const podilDisabled = lockMode === 'kc';
  const castkaDisabled = lockMode === 'pct';

  // Kategorie
  const soucetPodiluKategorii = (prodejna.kategorie || []).reduce((s, k) => s + Number(k.podil_procenta), 0);

  // -------- Handlers --------
  const setLockMode = (m) => onZmena({ lock_mode: m });
  const setServisLockMode = (m) => onZmena({ servis_lock_mode: m });

  /** Uživatel edituje podíl (%) – pokud byl lock 'kc', přepneme na 'pct'. */
  const onPodilChange = (val) => {
    const novyPodil = Math.min(100, Math.max(0, Number(val)));
    const zmeny = { podil_procenta: novyPodil };
    if (castkaFirma > 0) {
      zmeny.castka_prodejna = castkaFirma * novyPodil / 100;
    }
    if (lockMode === 'kc') zmeny.lock_mode = 'pct';
    onZmena(zmeny);
  };

  /** Uživatel edituje Kč prodejny – pokud byl lock 'pct', přepneme na 'kc'. */
  const onCastkaChange = (val) => {
    const num = Math.max(0, Number(val));
    const zmeny = { castka_prodejna: num };
    if (castkaFirma > 0) {
      zmeny.podil_procenta = Math.min(100, Math.max(0, (num / castkaFirma) * 100));
    }
    if (lockMode === 'pct') zmeny.lock_mode = 'kc';
    onZmena(zmeny);
  };

  const onProdejCastkaChange = (val) => {
    const num = Math.max(0, Number(val));
    const cp = Math.min(castkaRef, num);
    const zmeny = {
      castka_prodej: cp,
      castka_servis: Math.max(0, castkaRef - cp),
    };
    if (servisLockMode === 'pct') zmeny.servis_lock_mode = 'kc';
    onZmena(zmeny);
  };

  const onServisCastkaInputChange = (val) => {
    const num = Math.max(0, Number(val));
    const cs = Math.min(castkaRef, num);
    const zmeny = {
      castka_servis: cs,
      castka_prodej: Math.max(0, castkaRef - cs),
    };
    if (servisLockMode === 'pct') zmeny.servis_lock_mode = 'kc';
    onZmena(zmeny);
  };

  // Slider pro podíl v rámci prodejny (0-100)
  const onPodilSliderChange = (val) => {
    if (podilDisabled) return;
    onPodilChange(val);
  };

  const onServisSliderChange = (val) => {
    const cs = Math.min(castkaRef, Math.max(0, Number(val)));
    const zmeny = {
      castka_servis: cs,
      castka_prodej: Math.max(0, castkaRef - cs),
    };
    if (servisLockMode === 'pct') zmeny.servis_lock_mode = 'kc';
    onZmena(zmeny);
  };

  // Kategorie handlers
  const onKategorieLock = (kod, novyMode) => {
    const updatedKategorie = prodejna.kategorie.map(k =>
      k.kategorie_kod === kod ? { ...k, lock_mode: novyMode } : k
    );
    onZmena({ kategorie: updatedKategorie });
  };

  const onKategoriePodilChange = (kod, novyPodil) => {
    const novaHodnota = Math.min(100, Math.max(0, Number(novyPodil)));
    const updatedKategorie = prodejna.kategorie.map(k => {
      if (k.kategorie_kod !== kod) return k;
      const next = {
        ...k,
        podil_procenta: novaHodnota,
        castka_kategorie: castkaRef * novaHodnota / 100,
      };
      if (k.lock_mode === 'kc') next.lock_mode = 'pct';
      return next;
    });
    onZmena({ kategorie: updatedKategorie });
  };

  const onKategorieCastkaChange = (kod, novaCastka) => {
    const num = Math.max(0, Number(novaCastka));
    const updatedKategorie = prodejna.kategorie.map(k => {
      if (k.kategorie_kod !== kod) return k;
      const next = {
        ...k,
        castka_kategorie: num,
        podil_procenta: castkaRef > 0 ? Math.min(100, Math.max(0, (num / castkaRef) * 100)) : Number(k.podil_procenta),
      };
      if (k.lock_mode === 'pct') next.lock_mode = 'kc';
      return next;
    });
    onZmena({ kategorie: updatedKategorie });
  };

  const onPrumernaCenaChange = (kod, novaCena) => {
    const num = novaCena === '' || novaCena == null ? null : Number(novaCena);
    const updatedKategorie = prodejna.kategorie.map(k =>
      k.kategorie_kod === kod ? { ...k, prumerna_cena_za_kus: num } : k
    );
    onZmena({ kategorie: updatedKategorie });
  };

  const onKopirovatZProdejny = (zdrojProdejnaId) => {
    if (!zdrojProdejnaId) return;
    const zdroj = ostatniProdejny.find(p => p.prodejna_id === Number(zdrojProdejnaId));
    if (!zdroj || !zdroj.kategorie?.length) return;
    const zdrojMapa = Object.fromEntries(zdroj.kategorie.map(k => [k.kategorie_kod, k]));
    const updatedKategorie = prodejna.kategorie.map(k => {
      const zdrojKat = zdrojMapa[k.kategorie_kod];
      const novyPodil = zdrojKat != null ? Number(zdrojKat.podil_procenta) : Number(k.podil_procenta);
      return {
        ...k,
        podil_procenta: novyPodil,
        castka_kategorie: castkaRef * novyPodil / 100,
        prumerna_cena_za_kus: zdrojKat?.prumerna_cena_za_kus != null ? Number(zdrojKat.prumerna_cena_za_kus) : k.prumerna_cena_za_kus,
      };
    });
    onZmena({ kategorie: updatedKategorie });
  };

  const pocetKusu = (k, castkaKat) => {
    const cena = Number(k.prumerna_cena_za_kus);
    const c = castkaKat != null ? Number(castkaKat) : Number(k.castka_kategorie);
    return cena > 0 ? Math.ceil(c / cena) : null;
  };

  // Badge pod názvem prodejny
  const renderLockBadge = () => {
    if (lockMode === 'pct') {
      return (
        <span className="prodejna-lock-badge prodejna-lock-badge-pct" title="Zamčený podíl v %">
          🔒 {Number(podilInput).toFixed(1)} %
        </span>
      );
    }
    if (lockMode === 'kc') {
      return (
        <span className="prodejna-lock-badge prodejna-lock-badge-kc" title="Zamčená absolutní Kč">
          💰 {formatCastka(castkaInput)}
        </span>
      );
    }
    return (
      <span className="prodejna-lock-badge prodejna-lock-badge-auto" title="Dopočet">
        🔓 Auto
      </span>
    );
  };

  return (
    <div
      className={`prodejna-karta prodejna-karta-lock-${lockMode}`}
      style={{ borderLeftColor: prodejna.prodejna_barva || '#0066cc' }}
    >
      <div className="prodejna-karta-header">
        <div className="prodejna-info">
          <span className="prodejna-nazev">{prodejna.prodejna_nazev}</span>
          {renderLockBadge()}
          <span className="prodejna-castka-badge">
            {formatCastka(castkaShow)}
            {formatBezDphParenBadge(castkaShow)}
          </span>
        </div>
        <div className="prodejna-header-akce">
          <LockSegmented
            value={lockMode}
            onChange={setLockMode}
            size="md"
            title="Zámek prodejny: Auto / % / Kč"
          />
          <button
            className="plans-btn plans-btn-sm plans-btn-ghost"
            onClick={() => setRozbalene(!rozbalene)}
          >
            {rozbalene ? '▲ Skrýt kategorie' : '▼ Kategorie'}
          </button>
          {prodejna.id && (
            <button
              className="plans-btn plans-btn-sm plans-btn-ghost"
              onClick={() => setRozbaleneProdejci(!rozbaleneProdejci)}
            >
              {rozbaleneProdejci ? '▲ Skrýt prodejce' : '👥 Prodejci'}
            </button>
          )}
        </div>
      </div>

      {/* Slider podílu firmy (%) */}
      <div className={`prodejna-slider-row ${podilDisabled ? 'prodejna-slider-row-disabled' : 'prodejna-slider-row-primary'}`}>
        <label>Podíl na firmě</label>
        <div className="prodejna-slider-group">
          <input
            type="range"
            min="0"
            max="100"
            step="0.1"
            value={podilShow}
            onChange={e => onPodilSliderChange(e.target.value)}
            disabled={podilDisabled}
            className={`plans-slider ${lockMode === 'pct' ? 'plans-slider-locked-pct' : ''}`}
            title={podilDisabled ? 'Dopočteno z Kč – pro změnu přepněte zámek na %' : undefined}
          />
          <DraftNumberInput
            value={podilShow}
            onChange={onPodilChange}
            decimals={1}
            min={0}
            max={100}
            step="0.1"
            disabled={podilDisabled}
            className={`plans-input plans-input-sm ${lockMode === 'pct' ? 'plans-input-locked-pct' : ''}`}
            title={podilDisabled ? 'Dopočteno z Kč' : undefined}
          />
          <span className="plans-pct-label">%</span>
        </div>
      </div>

      {/* Kč prodejny – druhý řádek s Kč zámkem */}
      <div className={`prodejna-slider-row prodejna-slider-row-sub ${castkaDisabled ? 'prodejna-slider-row-disabled' : ''}`}>
        <label>Částka prodejny</label>
        <div className="prodejna-slider-group">
          <DraftNumberInput
            value={castkaShow}
            onChange={onCastkaChange}
            decimals={0}
            min={0}
            disabled={castkaDisabled}
            className={`plans-input plans-input-md ${lockMode === 'kc' ? 'plans-input-locked-kc' : ''}`}
            title={castkaDisabled ? 'Dopočteno z podílu %' : undefined}
          />
          <span className="plans-kc-label">Kč</span>
        </div>
      </div>

      {/* Slider prodej / servis */}
      <div className="prodejna-slider-row prodejna-slider-row-sub">
        <label>
          Servis
          <span className="prodejna-slider-lock-mini">
            <LockSegmented value={servisLockMode} onChange={setServisLockMode} size="sm" showLabels={false} title="Zámek prodej/servis" />
          </span>
        </label>
        <div className="prodejna-slider-group">
          <input
            type="range"
            min="0"
            max={Math.max(0, Math.round(castkaRef))}
            step="1000"
            value={Math.min(Math.max(0, Math.round(castkaServisShow)), Math.max(0, Math.round(castkaRef)))}
            onChange={e => onServisSliderChange(e.target.value)}
            className="plans-slider plans-slider-servis"
          />
          <span className="plans-prodej-servis-labels">
            <span className="label-prodej">
              Prodej:{' '}
              <DraftNumberInput
                value={Math.round(castkaProdejShow)}
                onChange={onProdejCastkaChange}
                decimals={0}
                min={0}
                max={Math.max(0, Math.round(castkaRef))}
                className="plans-input plans-input-sm plans-input-inline"
              />
              {' Kč'}
            </span>
            <span className="label-servis">
              Servis:{' '}
              <DraftNumberInput
                value={Math.round(castkaServisShow)}
                onChange={onServisCastkaInputChange}
                decimals={0}
                min={0}
                max={Math.max(0, Math.round(castkaRef))}
                className={`plans-input plans-input-sm plans-input-inline ${servisLockMode === 'kc' ? 'plans-input-locked-kc' : ''} ${servisLockMode === 'pct' ? 'plans-input-locked-pct' : ''}`}
              />
              {' Kč'}
            </span>
          </span>
        </div>
      </div>

      {/* Rozpad na kategorie */}
      {rozbalene && (
        <div className="prodejna-kategorie">
          <div className="prodejna-kategorie-header">
            <span>Kategorie</span>
            <span>Zámek</span>
            <span>Podíl</span>
            <span>Průměrná cena</span>
            <span>Částka</span>
            <span>Plán. kusy</span>
          </div>
          {ostatniProdejny.length > 0 && (
            <div className="prodejna-kopirovat-row">
              <label className="prodejna-kopirovat-label">Kopírovat z prodejny:</label>
              <select
                className="plans-select plans-select-sm"
                value=""
                onChange={e => {
                  const val = e.target.value;
                  if (val) {
                    onKopirovatZProdejny(val);
                    e.target.value = '';
                  }
                }}
                title="Vyberte prodejnu, ze které zkopírovat poměry kategorií"
              >
                <option value="">— vyberte prodejnu —</option>
                {ostatniProdejny.map(p => (
                  <option key={p.prodejna_id} value={p.prodejna_id}>
                    {p.prodejna_nazev}
                  </option>
                ))}
              </select>
            </div>
          )}
          {prodejna.kategorie.map(k => {
            const kLock = k.lock_mode || 'none';
            const kPodilShow = k.podil_procenta_dopocet != null ? Number(k.podil_procenta_dopocet) : Number(k.podil_procenta);
            const kCastkaShow = k.castka_kategorie_dopocet != null ? Number(k.castka_kategorie_dopocet) : Number(k.castka_kategorie);
            const kPodilDisabled = kLock === 'kc';
            const kCastkaDisabled = kLock === 'pct';
            return (
              <div
                key={k.kategorie_kod}
                className={`kategorie-radek kategorie-lock-${kLock}`}
              >
                <div className="kategorie-nazev-wrap">
                  <span className="kategorie-nazev">{KATEGORIE_NAZVY[k.kategorie_kod] || k.kategorie_kod}</span>
                </div>
                <div className="kategorie-lock-wrap">
                  <LockSegmented
                    value={kLock}
                    onChange={(m) => onKategorieLock(k.kategorie_kod, m)}
                    size="sm"
                    showLabels={false}
                    title="Zámek kategorie"
                  />
                </div>
                <div className="kategorie-slider-group">
                  <input
                    type="range"
                    min="0"
                    max="100"
                    step="0.5"
                    value={Number(kPodilShow).toFixed(1)}
                    onChange={e => onKategoriePodilChange(k.kategorie_kod, e.target.value)}
                    disabled={kPodilDisabled}
                    className={`plans-slider plans-slider-kategorie ${kLock === 'pct' ? 'plans-slider-locked-pct' : ''}`}
                    title={kPodilDisabled ? 'Dopočteno z Kč' : undefined}
                  />
                  <DraftNumberInput
                    value={kPodilShow}
                    onChange={(v) => onKategoriePodilChange(k.kategorie_kod, v)}
                    decimals={1}
                    min={0}
                    max={100}
                    step="0.1"
                    disabled={kPodilDisabled}
                    className={`plans-input plans-input-sm ${kLock === 'pct' ? 'plans-input-locked-pct' : ''}`}
                    title={kPodilDisabled ? 'Dopočteno z Kč' : undefined}
                  />
                  <span className="plans-pct-label">%</span>
                </div>
                <DraftNumberInput
                  value={k.prumerna_cena_za_kus != null ? Number(k.prumerna_cena_za_kus) : ''}
                  onChange={(v) => onPrumernaCenaChange(k.kategorie_kod, v)}
                  decimals={0}
                  min={0}
                  placeholder="—"
                  className="plans-input plans-input-sm"
                />
                <DraftNumberInput
                  value={kCastkaShow}
                  onChange={(v) => onKategorieCastkaChange(k.kategorie_kod, v)}
                  decimals={0}
                  min={0}
                  disabled={kCastkaDisabled}
                  className={`plans-input plans-input-sm kategorie-castka ${kLock === 'kc' ? 'plans-input-locked-kc' : ''}`}
                  title={kCastkaDisabled ? 'Dopočteno z podílu %' : undefined}
                />
                <span className="kategorie-kusy">
                  {pocetKusu(k, kCastkaShow) != null ? pocetKusu(k, kCastkaShow).toLocaleString('cs-CZ') : '—'}
                </span>
              </div>
            );
          })}
          <div className="kategorie-soucet">
            <span>Součet: {soucetPodiluKategorii.toFixed(1)} %</span>
          </div>
        </div>
      )}

      {rozbaleneProdejci && prodejna.id && (
        <PlanProdejcuPanel planProdejnaId={prodejna.id} />
      )}
    </div>
  );
}
