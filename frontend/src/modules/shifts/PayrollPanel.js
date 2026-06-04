import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import {
    PRODUCT_COMMISSIONS,
    SERVIS_BREAKDOWN_KEY,
    BREAKDOWN_LINE_LABELS,
    INFO_ONLY_COMMISSIONS,
} from '../../constants/productCommissions';
import { formatPoints, formatNumber } from '../../utils/formatBody';
import { manualNumberInputClass, preventNumberInputWheel } from '../../utils/manualNumberInput';
import { useModalKeyboard } from '../../utils/useModalKeyboard';
import './PayrollPanel.css';

const MONTH_NAMES = [
    'Leden', 'Únor', 'Březen', 'Duben', 'Květen', 'Červen',
    'Červenec', 'Srpen', 'Září', 'Říjen', 'Listopad', 'Prosinec',
];

function formatMonthName(monthStr) {
    const [year, month] = monthStr.split('-').map(Number);
    return `${MONTH_NAMES[month - 1]} ${year}`;
}

function currentMonthStr() {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
}

/** Posledních 36 měsíců (včetně aktuálního) pro výběr v pickeru. */
function buildMonthOptions(count = 36) {
    const options = [];
    const now = new Date();
    for (let i = 0; i < count; i += 1) {
        const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
        const value = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
        options.push({ value, label: formatMonthName(value) });
    }
    return options;
}

function PayrollPanel({ month, onMonthChange, onExport }) {
    const [rows, setRows] = useState([]);
    const [fonduH, setFonduH] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [expandedId, setExpandedId] = useState(null);
    const [showOdmenaModal, setShowOdmenaModal] = useState(false);
    const [showPenalizaceModal, setShowPenalizaceModal] = useState(false);
    const [savingOdmena, setSavingOdmena] = useState(false);
    const [savingPenalizace, setSavingPenalizace] = useState(false);
    const [monthPickerOpen, setMonthPickerOpen] = useState(false);
    const [odmenaForm, setOdmenaForm] = useState({ user_id: '', castka: '', poznamka: '' });
    const [penalizaceForm, setPenalizaceForm] = useState({ user_id: '', duvod: '' });
    const monthPickerRef = useRef(null);
    const odmenaFormRef = useRef(null);
    const penalizaceFormRef = useRef(null);

    const closeOdmenaModal = useCallback(() => {
        setShowOdmenaModal(false);
        setOdmenaForm({ user_id: '', castka: '', poznamka: '' });
    }, []);

    const closePenalizaceModal = useCallback(() => {
        setShowPenalizaceModal(false);
        setPenalizaceForm({ user_id: '', duvod: '' });
    }, []);

    useModalKeyboard(showOdmenaModal, { onClose: closeOdmenaModal, formRef: odmenaFormRef });
    useModalKeyboard(showPenalizaceModal, { onClose: closePenalizaceModal, formRef: penalizaceFormRef });

    const monthOptions = useMemo(() => buildMonthOptions(48), []);

    const soucetBodu = useMemo(
        () => rows.reduce((s, r) => s + (Number(r.celkem_body) || 0), 0),
        [rows],
    );

    const loadPayroll = useCallback(async () => {
        if (!month) return;
        setLoading(true);
        setError('');
        try {
            const res = await fetch(`/api/shifts/payroll/?mesic=${month}`, { credentials: 'include' });
            if (!res.ok) {
                const data = await res.json().catch(() => ({}));
                throw new Error(data.error || 'Chyba při načítání výplaty');
            }
            const data = await res.json();
            setRows(data.rows || []);
            const fond = data.fondu_h ?? data.rows?.[0]?.fondu_h ?? null;
            setFonduH(fond);
        } catch (e) {
            setError(e.message);
            setRows([]);
            setFonduH(null);
        } finally {
            setLoading(false);
        }
    }, [month]);

    useEffect(() => {
        loadPayroll();
    }, [loadPayroll]);

    useEffect(() => {
        const onDocClick = (e) => {
            if (monthPickerRef.current && !monthPickerRef.current.contains(e.target)) {
                setMonthPickerOpen(false);
            }
        };
        document.addEventListener('mousedown', onDocClick);
        return () => document.removeEventListener('mousedown', onDocClick);
    }, []);

    const employeeOptions = useMemo(
        () => rows.map((r) => ({ id: r.user_id, jmeno: r.jmeno })),
        [rows],
    );

    const savePenalizace = async (e) => {
        e.preventDefault();
        const duvod = (penalizaceForm.duvod || '').trim();
        if (!penalizaceForm.user_id || !duvod) {
            alert('Vyberte zaměstnance a zadejte důvod srážky.');
            return;
        }
        setSavingPenalizace(true);
        try {
            const res = await fetch('/api/shifts/payroll/penalizace/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({
                    user_id: parseInt(penalizaceForm.user_id, 10),
                    mesic: month,
                    duvod,
                }),
            });
            if (!res.ok) {
                const data = await res.json().catch(() => ({}));
                throw new Error(data.error || 'Uložení selhalo');
            }
            closePenalizaceModal();
            await loadPayroll();
        } catch (err) {
            alert(err.message);
        } finally {
            setSavingPenalizace(false);
        }
    };

    const saveOdmena = async (e) => {
        e.preventDefault();
        const castka = parseFloat(odmenaForm.castka);
        if (!odmenaForm.user_id || Number.isNaN(castka) || castka <= 0) {
            alert('Vyberte zaměstnance a zadejte kladný počet bodů.');
            return;
        }
        setSavingOdmena(true);
        try {
            const res = await fetch('/api/shifts/payroll/odmena/', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({
                    user_id: parseInt(odmenaForm.user_id, 10),
                    mesic: month,
                    castka,
                    poznamka: odmenaForm.poznamka || '',
                    add: true,
                }),
            });
            if (!res.ok) {
                const data = await res.json().catch(() => ({}));
                throw new Error(data.error || 'Uložení selhalo');
            }
            closeOdmenaModal();
            await loadPayroll();
        } catch (err) {
            alert(err.message);
        } finally {
            setSavingOdmena(false);
        }
    };

    const renderProvizeBreakdown = (breakdown) => {
        if (!breakdown) return null;
        const lines = [];
        PRODUCT_COMMISSIONS.forEach(({ key }) => {
            const item = breakdown[key];
            if (item && (item.count > 0 || item.points > 0)) {
                lines.push(
                    <div key={key} className="breakdown-line">
                        <span className="breakdown-label">{BREAKDOWN_LINE_LABELS[key]}</span>
                        <span className="breakdown-value">{item.count}× → {formatPoints(item.points)}</span>
                    </div>
                );
            }
        });
        const servis = breakdown[SERVIS_BREAKDOWN_KEY];
        if (servis && servis.points > 0) {
            lines.push(
                <div key="servis" className="breakdown-line">
                    <span className="breakdown-label">{BREAKDOWN_LINE_LABELS[SERVIS_BREAKDOWN_KEY]}</span>
                    <span className="breakdown-value">{formatPoints(servis.points)}</span>
                </div>
            );
        }
        INFO_ONLY_COMMISSIONS.forEach(({ key, label }) => {
            const item = breakdown[key];
            if (item && item.count > 0) {
                lines.push(
                    <div key={key} className="breakdown-line breakdown-line-info">
                        <span className="breakdown-label">{label}</span>
                        <span className="breakdown-value">{item.count} ks (jen výpis)</span>
                    </div>
                );
            }
        });
        return lines.length ? (
            <div className="payroll-detail-section">
                <h4>Provize z prodeje</h4>
                <div className="payroll-breakdown payroll-breakdown-grid">{lines}</div>
            </div>
        ) : null;
    };

    const renderBrigadnikSouhrn = (row) => {
        if (!row.is_brigadnik) return null;
        const vypomocH = Number(row.vypomoc_h) || 0;
        const prodejceH = Number(row.prodejce_h) || 0;
        const sazbaProdejce = row.body_za_hodinu ?? 0;
        const sazbaVypomoc = row.body_vypomoc_za_hodinu ?? 150;
        const zaklad = Number(row.zaklad_body) || 0;
        const provize = Number(row.provize_body) || 0;
        const celkem = Number(row.celkem_body) || 0;
        return (
            <div className="payroll-detail-section">
                <h4>Výpočet brigádníka</h4>
                <div className="payroll-breakdown payroll-breakdown-grid">
                    {vypomocH > 0 && (
                        <div className="breakdown-line">
                            <span className="breakdown-label">Výpomoc</span>
                            <span className="breakdown-value">
                                {formatNumber(vypomocH)} h × {sazbaVypomoc} = {formatPoints(vypomocH * sazbaVypomoc)}
                            </span>
                        </div>
                    )}
                    {prodejceH > 0 && (
                        <div className="breakdown-line">
                            <span className="breakdown-label">Jako prodejce</span>
                            <span className="breakdown-value">
                                {formatNumber(prodejceH)} h × {sazbaProdejce} = {formatPoints(prodejceH * sazbaProdejce)}
                            </span>
                        </div>
                    )}
                    <div className="breakdown-line">
                        <span className="breakdown-label">Hodiny celkem (základ)</span>
                        <span className="breakdown-value">{formatPoints(zaklad)}</span>
                    </div>
                    <div className="breakdown-line">
                        <span className="breakdown-label">+ Provize (body z prodeje)</span>
                        <span className="breakdown-value">{formatPoints(provize)}</span>
                    </div>
                    {(row.dyska_body || 0) > 0 && (
                        <div className="breakdown-line">
                            <span className="breakdown-label">
                                + Dýška / vícepráce P63615
                                {(row.dyska_kusy || 0) > 0 ? ` (${row.dyska_kusy} ks)` : ''}
                            </span>
                            <span className="breakdown-value">{formatPoints(row.dyska_body)}</span>
                        </div>
                    )}
                    {(row.doplnky_body > 0 || row.odmena_mesic_body > 0) && (
                        <div className="breakdown-line">
                            <span className="breakdown-label">+ Doplňky / měsíční bonus</span>
                            <span className="breakdown-value">
                                {formatPoints((row.doplnky_body || 0) + (row.odmena_mesic_body || 0))}
                            </span>
                        </div>
                    )}
                    <div className="breakdown-line breakdown-line-total">
                        <span className="breakdown-label">Celkem</span>
                        <span className="breakdown-value"><strong>{formatPoints(celkem)}</strong></span>
                    </div>
                </div>
            </div>
        );
    };

    const renderMzdaSouhrn = (row) => {
        if (row.is_brigadnik) return null;
        const zaklad = Number(row.zaklad_body) || 0;
        const doplnky = row.doplnky || [];
        const cestovne = Number(row.cestovne_body) || 0;
        const prescas = Number(row.prescas_body) || 0;
        const prescasH = Number(row.prescas_h) || 0;
        const sazbaPrescas = row.prescas_sazba_h ?? row.viceprace_sazba_h;
        const dyska = Number(row.dyska_body) || 0;
        const dyskaKusy = Number(row.dyska_kusy) || 0;
        const zakladVp = row.zaklad_pro_vicepraci_body;
        const dovolena = Number(row.dovolena_body) || 0;
        const manual = Number(row.odmena_mesic_body) || 0;
        const provize = Number(row.provize_body) || 0;
        const fixni = Number(row.mzda_fixni_body) || 0;
        const celkem = Number(row.celkem_body) || 0;
        const fond = row.fondu_h;

        const lines = [];
        lines.push(
            <div key="zaklad" className="breakdown-line">
                <span className="breakdown-label">Základ (fixní body)</span>
                <span className="breakdown-value">{formatPoints(zaklad)}</span>
            </div>
        );
        doplnky.forEach((d, i) => {
            lines.push(
                <div key={`d-${i}`} className="breakdown-line">
                    <span className="breakdown-label">+ {d.nazev}</span>
                    <span className="breakdown-value">{formatPoints(d.castka)}</span>
                </div>
            );
        });
        if (doplnky.length > 0) {
            lines.push(
                <div key="fixni" className="breakdown-line">
                    <span className="breakdown-label">= Fixní celkem</span>
                    <span className="breakdown-value">{formatPoints(fixni)}</span>
                </div>
            );
        }
        if (cestovne > 0) {
            lines.push(
                <div key="cestovne" className="breakdown-line">
                    <span className="breakdown-label">+ Cestovné (profil, měsíčně)</span>
                    <span className="breakdown-value">{formatPoints(cestovne)}</span>
                </div>
            );
        }
        const provizeBrutto = Number(row.provize_body_brutto ?? row.provize_body) || 0;
        const srazka = Number(row.penalizace_srazka_body) || 0;
        if (srazka > 0 && provizeBrutto > provize) {
            lines.push(
                <div key="provize-brutto" className="breakdown-line">
                    <span className="breakdown-label">+ Provize z prodeje (hrubá)</span>
                    <span className="breakdown-value">{formatPoints(provizeBrutto)}</span>
                </div>
            );
            (row.penalizace || []).forEach((p, i) => {
                lines.push(
                    <div key={`pen-${i}`} className="breakdown-line breakdown-line-deduction">
                        <span className="breakdown-label">− Penalizace −10 %: {p.duvod}</span>
                        <span className="breakdown-value">—</span>
                    </div>
                );
            });
            lines.push(
                <div key="provize-srazka" className="breakdown-line breakdown-line-deduction">
                    <span className="breakdown-label">
                        − Srážka z provize ({row.penalizace_procent || 0} %)
                    </span>
                    <span className="breakdown-value">−{formatPoints(srazka)}</span>
                </div>
            );
        }
        lines.push(
            <div key="provize" className="breakdown-line">
                <span className="breakdown-label">+ Provize z prodeje{ srazka > 0 ? ' (po srážkách)' : ''}</span>
                <span className="breakdown-value">{formatPoints(provize)}</span>
            </div>
        );
        if (dovolena > 0) {
            lines.push(
                <div key="dovolena" className="breakdown-line">
                    <span className="breakdown-label">
                        + Dovolená ({formatNumber(row.dovolena_h)} h × {formatPoints(row.prumer_fixni_h)}/h)
                    </span>
                    <span className="breakdown-value">{formatPoints(dovolena)}</span>
                </div>
            );
        }
        if (dyska > 0) {
            lines.push(
                <div key="dyska" className="breakdown-line">
                    <span className="breakdown-label">
                        + Dýška / vícepráce P63615
                        {dyskaKusy > 0 ? ` (${dyskaKusy} ks)` : ''}
                    </span>
                    <span className="breakdown-value">{formatPoints(dyska)}</span>
                </div>
            );
        }
        if (prescas > 0) {
            const sazbaLabel = sazbaPrescas != null && zakladVp != null && fond
                ? `${formatPoints(zakladVp)} / ${formatNumber(fond)} h = ${formatPoints(sazbaPrescas)}/h`
                : null;
            lines.push(
                <div key="prescas" className="breakdown-line">
                    <span className="breakdown-label">
                        + Přesčas ({formatNumber(prescasH)} h
                        {sazbaLabel ? `, ${sazbaLabel}` : ''})
                    </span>
                    <span className="breakdown-value">{formatPoints(prescas)}</span>
                </div>
            );
        }
        if (manual > 0) {
            lines.push(
                <div key="manual" className="breakdown-line">
                    <span className="breakdown-label">
                        + Manuální příplatek
                        {row.odmena_mesic_poznamka ? ` (${row.odmena_mesic_poznamka})` : ''}
                    </span>
                    <span className="breakdown-value">{formatPoints(manual)}</span>
                </div>
            );
        }
        lines.push(
            <div key="celkem" className="breakdown-line breakdown-line-total">
                <span className="breakdown-label">Celkem</span>
                <span className="breakdown-value"><strong>{formatPoints(celkem)}</strong></span>
            </div>
        );

        return (
            <div className="payroll-detail-section">
                <h4>Výpočet výplaty</h4>
                <div className="payroll-breakdown payroll-breakdown-grid">{lines}</div>
            </div>
        );
    };

    if (loading && rows.length === 0) {
        return <div className="payroll-panel loading">Načítání výplaty…</div>;
    }

    return (
        <div className="payroll-panel">
            <div className="payroll-controls shifts-controls">
                <div className="payroll-month-block" ref={monthPickerRef}>
                    <div className="month-navigation">
                        <button
                            type="button"
                            className="nav-btn"
                            onClick={() => {
                                const idx = monthOptions.findIndex((o) => o.value === month);
                                if (idx < monthOptions.length - 1) {
                                    onMonthChange?.(monthOptions[idx + 1].value);
                                }
                            }}
                            title="Předchozí měsíc"
                        >
                            ◀
                        </button>
                        <button
                            type="button"
                            className="month-picker-trigger"
                            onClick={() => setMonthPickerOpen((v) => !v)}
                        >
                            {formatMonthName(month)}
                            <span className="picker-caret">{monthPickerOpen ? '▲' : '▼'}</span>
                        </button>
                        <button
                            type="button"
                            className="nav-btn"
                            onClick={() => {
                                const idx = monthOptions.findIndex((o) => o.value === month);
                                if (idx > 0) {
                                    onMonthChange?.(monthOptions[idx - 1].value);
                                }
                            }}
                            title="Následující měsíc"
                        >
                            ▶
                        </button>
                    </div>
                    {monthPickerOpen && (
                        <div className="month-picker-dropdown">
                            <button
                                type="button"
                                className="month-picker-today"
                                onClick={() => {
                                    onMonthChange?.(currentMonthStr());
                                    setMonthPickerOpen(false);
                                }}
                            >
                                Aktuální měsíc
                            </button>
                            <ul className="month-picker-list">
                                {monthOptions.map((opt) => (
                                    <li key={opt.value}>
                                        <button
                                            type="button"
                                            className={opt.value === month ? 'active' : ''}
                                            onClick={() => {
                                                onMonthChange?.(opt.value);
                                                setMonthPickerOpen(false);
                                            }}
                                        >
                                            {opt.label}
                                        </button>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    )}
                </div>

                <div className="payroll-stats stats-grid">
                    <div className="stat-card primary">
                        <div className="stat-content">
                            <div className="stat-value">{formatPoints(soucetBodu)}</div>
                            <div className="stat-label">Součet bodů za měsíc</div>
                        </div>
                    </div>
                    <div className="stat-card success">
                        <div className="stat-content">
                            <div className="stat-value">
                                {fonduH != null ? `${formatNumber(fonduH)} h` : '—'}
                            </div>
                            <div className="stat-label">Měsíční fond</div>
                        </div>
                    </div>
                </div>

                <div className="payroll-actions action-buttons">
                    <button
                        type="button"
                        className="btn-primary"
                        onClick={() => setShowOdmenaModal(true)}
                    >
                        + Přidej odměnu
                    </button>
                    <button
                        type="button"
                        className="btn-secondary"
                        onClick={() => setShowPenalizaceModal(true)}
                    >
                        + Penalizace −10 %
                    </button>
                    {onExport && (
                        <button type="button" className="btn-export" onClick={onExport}>
                            📊 Export
                        </button>
                    )}
                </div>
            </div>

            {loading && <p className="payroll-loading-inline">Aktualizuji data…</p>}

            <p className="payroll-hint">
                Rozklikněte řádek pro detail (vedoucí, cestovné, přesčas, provize).
                Přesčas = (základ + variabilní z profilu) / fond × hodiny nad fondem. Dýška = obrat P63615 (1 bod = 1 Kč).
                Cestovné a manuální bonus se do sazby přesčasu nepřičítají.
            </p>

            {error && <div className="error-message">{error}</div>}

            <div className="payroll-table-wrap">
                <table className="payroll-table">
                    <thead>
                        <tr>
                            <th className="col-expand" />
                            <th>Jméno</th>
                            <th>Odprac. h</th>
                            <th>Fixní</th>
                            <th>Provize</th>
                            <th>Celkem</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows.map((row) => {
                            const isOpen = expandedId === row.user_id;
                            return (
                                <React.Fragment key={row.user_id}>
                                    <tr className={isOpen ? 'row-expanded' : ''}>
                                        <td className="col-expand">
                                            <button
                                                type="button"
                                                className="expand-btn"
                                                onClick={() => setExpandedId(isOpen ? null : row.user_id)}
                                                aria-expanded={isOpen}
                                            >
                                                {isOpen ? '▼' : '▶'}
                                            </button>
                                        </td>
                                        <td className="col-name">{row.jmeno}</td>
                                        <td>{formatNumber(row.odpracovano_h)}</td>
                                        <td
                                            title={
                                                row.is_brigadnik
                                                    ? `${row.body_za_hodinu} bodů/h × ${row.odpracovano_h} h`
                                                    : (row.doplnky_body > 0
                                                        ? `Základ ${row.zaklad_body} + doplňky ${row.doplnky_body}`
                                                        : undefined)
                                            }
                                        >
                                            {formatPoints(row.mzda_fixni_body)}
                                            {row.is_brigadnik && row.body_za_hodinu != null && (
                                                <span className="payroll-sazba-hint"> ({row.body_za_hodinu}/h)</span>
                                            )}
                                        </td>
                                        <td>{formatPoints(row.provize_body)}</td>
                                        <td className="col-celkem"><strong>{formatPoints(row.celkem_body)}</strong></td>
                                    </tr>
                                    {isOpen && (
                                        <tr className="detail-row">
                                            <td colSpan={6}>
                                                <div className="payroll-detail-full">
                                    {renderBrigadnikSouhrn(row)}
                                    {renderMzdaSouhrn(row)}
                                    {row.deficit_h > 0 && (
                                        <p className="payroll-detail-hint">
                                            Deficit fondu v měsíci: {formatNumber(row.deficit_h)} h (odečteno z roční dovolené).
                                        </p>
                                    )}
                                    {renderProvizeBreakdown(row.provize_breakdown)}
                                                </div>
                                            </td>
                                        </tr>
                                    )}
                                </React.Fragment>
                            );
                        })}
                    </tbody>
                    {rows.length > 0 && (
                        <tfoot>
                            <tr className="payroll-tfoot">
                                <td colSpan={5} className="tfoot-label">Součet bodů</td>
                                <td className="col-celkem"><strong>{formatPoints(soucetBodu)}</strong></td>
                            </tr>
                        </tfoot>
                    )}
                </table>
            </div>

            {showPenalizaceModal && (
                <div className="payroll-modal-overlay" onClick={closePenalizaceModal}>
                    <div className="payroll-modal" onClick={(e) => e.stopPropagation()}>
                        <h3>Penalizace −10 % z provize</h3>
                        <p className="modal-hint">
                            Každá penalizace sníží provizi o dalších 10 % (3× = −30 %). Základ, cestovné
                            a bonusy se nemění. Měsíc: {formatMonthName(month)}.
                        </p>
                        <form ref={penalizaceFormRef} onSubmit={savePenalizace}>
                            <label>
                                Zaměstnanec
                                <select
                                    value={penalizaceForm.user_id}
                                    onChange={(e) => setPenalizaceForm((f) => ({ ...f, user_id: e.target.value }))}
                                    required
                                >
                                    <option value="">— vyberte —</option>
                                    {employeeOptions.map((u) => (
                                        <option key={u.id} value={u.id}>{u.jmeno}</option>
                                    ))}
                                </select>
                            </label>
                            <label>
                                Důvod srážky
                                <input
                                    type="text"
                                    value={penalizaceForm.duvod}
                                    onChange={(e) => setPenalizaceForm((f) => ({ ...f, duvod: e.target.value }))}
                                    required
                                />
                            </label>
                            <div className="modal-actions">
                                <button type="button" className="btn-cancel" onClick={closePenalizaceModal}>
                                    Zrušit
                                </button>
                                <button type="submit" className="btn-primary" disabled={savingPenalizace}>
                                    {savingPenalizace ? 'Ukládám…' : 'Přidat penalizaci'}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {showOdmenaModal && (
                <div className="payroll-modal-overlay" onClick={closeOdmenaModal}>
                    <div className="payroll-modal" onClick={(e) => e.stopPropagation()}>
                        <h3>Přidej odměnu</h3>
                        <p className="modal-hint">
                            Body se přičtou k měsíční odměně za {formatMonthName(month)}.
                        </p>
                        <form ref={odmenaFormRef} onSubmit={saveOdmena}>
                            <label>
                                Zaměstnanec
                                <select
                                    value={odmenaForm.user_id}
                                    onChange={(e) => setOdmenaForm((f) => ({ ...f, user_id: e.target.value }))}
                                    required
                                >
                                    <option value="">— vyberte —</option>
                                    {employeeOptions.map((u) => (
                                        <option key={u.id} value={u.id}>{u.jmeno}</option>
                                    ))}
                                </select>
                            </label>
                            <label>
                                Body
                                <input
                                    type="number"
                                    className={manualNumberInputClass()}
                                    min="1"
                                    step="1"
                                    value={odmenaForm.castka}
                                    onChange={(e) => setOdmenaForm((f) => ({ ...f, castka: e.target.value }))}
                                    onWheel={preventNumberInputWheel}
                                    required
                                />
                            </label>
                            <label>
                                Poznámka (volitelné)
                                <input
                                    type="text"
                                    value={odmenaForm.poznamka}
                                    onChange={(e) => setOdmenaForm((f) => ({ ...f, poznamka: e.target.value }))}
                                />
                            </label>
                            <div className="modal-actions">
                                <button type="button" className="btn-cancel" onClick={closeOdmenaModal}>
                                    Zrušit
                                </button>
                                <button type="submit" className="btn-primary" disabled={savingOdmena}>
                                    {savingOdmena ? 'Ukládám…' : 'Přidat'}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}

export default PayrollPanel;
