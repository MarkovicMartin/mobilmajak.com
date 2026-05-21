import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import {
    PRODUCT_COMMISSIONS,
    SERVIS_BREAKDOWN_KEY,
    BREAKDOWN_LINE_LABELS,
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
    const [savingOdmena, setSavingOdmena] = useState(false);
    const [monthPickerOpen, setMonthPickerOpen] = useState(false);
    const [odmenaForm, setOdmenaForm] = useState({ user_id: '', castka: '', poznamka: '' });
    const monthPickerRef = useRef(null);
    const odmenaFormRef = useRef(null);

    const closeOdmenaModal = useCallback(() => {
        setShowOdmenaModal(false);
        setOdmenaForm({ user_id: '', castka: '', poznamka: '' });
    }, []);

    useModalKeyboard(showOdmenaModal, { onClose: closeOdmenaModal, formRef: odmenaFormRef });

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
        return lines.length ? (
            <div className="payroll-detail-section">
                <h4>Provize z prodeje</h4>
                <div className="payroll-breakdown payroll-breakdown-grid">{lines}</div>
            </div>
        ) : null;
    };

    const renderBonusy = (row) => {
        const items = [];
        (row.doplnky || []).forEach((d, i) => {
            items.push(
                <div key={`d-${i}`} className="breakdown-line">
                    <span className="breakdown-label">{d.nazev}</span>
                    <span className="breakdown-value">{formatPoints(d.castka)}</span>
                </div>
            );
        });
        if ((row.odmena_mesic_body || 0) > 0) {
            items.push(
                <div key="odmena" className="breakdown-line">
                    <span className="breakdown-label">
                        Měsíční bonus
                        {row.odmena_mesic_poznamka ? ` (${row.odmena_mesic_poznamka})` : ''}
                    </span>
                    <span className="breakdown-value">{formatPoints(row.odmena_mesic_body)}</span>
                </div>
            );
        }
        if (!items.length) return null;
        return (
            <div className="payroll-detail-section">
                <h4>Bonusy</h4>
                <div className="payroll-breakdown payroll-breakdown-grid">{items}</div>
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
                    {onExport && (
                        <button type="button" className="btn-export" onClick={onExport}>
                            📊 Export
                        </button>
                    )}
                </div>
            </div>

            {loading && <p className="payroll-loading-inline">Aktualizuji data…</p>}

            <p className="payroll-hint">
                Fixní body / sazba za hodinu a doplňky v modulu <strong>Uživatelé</strong> (brigádník: hodiny × sazba).
                Měsíční bonus přidáte tlačítkem výše.
            </p>

            {error && <div className="error-message">{error}</div>}

            <div className="payroll-table-wrap">
                <table className="payroll-table">
                    <thead>
                        <tr>
                            <th className="col-expand" />
                            <th>Jméno</th>
                            <th>Odprac. h</th>
                            <th>Přesčas h</th>
                            <th>Fixní / hodiny</th>
                            <th>Doplňky</th>
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
                                        <td>{formatNumber(row.prescas_h)}</td>
                                        <td
                                            title={
                                                row.is_brigadnik
                                                    ? `${row.body_za_hodinu} bodů/h × ${row.odpracovano_h} h`
                                                    : undefined
                                            }
                                        >
                                            {formatPoints(row.zaklad_body)}
                                            {row.is_brigadnik && row.body_za_hodinu != null && (
                                                <span className="payroll-sazba-hint"> ({row.body_za_hodinu}/h)</span>
                                            )}
                                        </td>
                                        <td>{formatPoints(row.doplnky_body)}</td>
                                        <td>{formatPoints(row.provize_body)}</td>
                                        <td className="col-celkem"><strong>{formatPoints(row.celkem_body)}</strong></td>
                                    </tr>
                                    {isOpen && (
                                        <tr className="detail-row">
                                            <td colSpan={8}>
                                                <div className="payroll-detail-full">
                                                    {renderProvizeBreakdown(row.provize_breakdown)}
                                                    {renderBonusy(row)}
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
                                <td colSpan={7} className="tfoot-label">Součet bodů</td>
                                <td className="col-celkem"><strong>{formatPoints(soucetBodu)}</strong></td>
                            </tr>
                        </tfoot>
                    )}
                </table>
            </div>

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
