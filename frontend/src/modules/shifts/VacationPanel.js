import React, { useState, useEffect, useCallback, useRef } from 'react';
import { formatPoints, formatNumber } from '../../utils/formatBody';
import './VacationPanel.css';

const MONTH_NAMES = [
    'Leden', 'Únor', 'Březen', 'Duben', 'Květen', 'Červen',
    'Červenec', 'Srpen', 'Září', 'Říjen', 'Listopad', 'Prosinec',
];

const CACHE_PREFIX = 'vacation-overview-v4';
const CURRENT_YEAR_STALE_MS = 5 * 60 * 1000;
const memoryCache = new Map();

function cacheKey(rok) {
    return `${CACHE_PREFIX}:${rok}`;
}

function readCache(rok) {
    const mem = memoryCache.get(rok);
    if (mem) return mem;
    try {
        const raw = sessionStorage.getItem(cacheKey(rok));
        if (!raw) return null;
        const parsed = JSON.parse(raw);
        memoryCache.set(rok, parsed);
        return parsed;
    } catch {
        return null;
    }
}

function writeCache(rok, payload) {
    const entry = { ...payload, fetchedAt: Date.now() };
    memoryCache.set(rok, entry);
    try {
        sessionStorage.setItem(cacheKey(rok), JSON.stringify(entry));
    } catch {
        // sessionStorage plné – modulová cache stačí
    }
}

function applyOverviewPayload(data, setEligible, setMessage, setUsers, setExpandedId) {
    setEligible(data.eligible !== false);
    setMessage(data.message || '');
    const list = data.users || [];
    setUsers(list);
    if (list.length === 1) {
        setExpandedId(list[0].user_id);
    }
}

function needsBackgroundRefresh(rok, cached, now = new Date()) {
    if (!cached) return true;
    const currentYear = now.getFullYear();
    // Uzavřené roky se nemění – stačí cache ze session.
    if (rok < currentYear) return false;
    if (rok > currentYear) return true;
    // Běžící rok: na pozadí max. jednou za 5 min (hlavička + měsíční tabulka z API).
    return Date.now() - (cached.fetchedAt || 0) > CURRENT_YEAR_STALE_MS;
}

function VacationPanel({ user }) {
    const [rok, setRok] = useState(() => new Date().getFullYear());
    const [users, setUsers] = useState([]);
    const [eligible, setEligible] = useState(true);
    const [message, setMessage] = useState('');
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [expandedId, setExpandedId] = useState(null);
    const fetchSeq = useRef(0);

    const loadOverview = useCallback(async () => {
        const seq = ++fetchSeq.current;
        const cached = readCache(rok);
        const hasCachedUsers = Boolean(cached?.data?.users?.length);

        if (cached?.data) {
            applyOverviewPayload(cached.data, setEligible, setMessage, setUsers, setExpandedId);
            setLoading(false);
        } else {
            setLoading(true);
        }
        setError('');

        if (!needsBackgroundRefresh(rok, cached)) {
            return;
        }

        try {
            const res = await fetch(`/api/shifts/vacation-overview/?rok=${rok}`, {
                credentials: 'include',
            });
            if (!res.ok) {
                const data = await res.json().catch(() => ({}));
                throw new Error(data.error || 'Chyba při načítání dovolené');
            }
            const data = await res.json();
            if (seq !== fetchSeq.current) return;

            const merged = { ...data, users: data.users || [] };

            writeCache(rok, { data: merged });
            applyOverviewPayload(merged, setEligible, setMessage, setUsers, setExpandedId);
        } catch (e) {
            if (seq !== fetchSeq.current) return;
            if (!hasCachedUsers) {
                setError(e.message);
                setUsers([]);
            }
        } finally {
            if (seq === fetchSeq.current) {
                setLoading(false);
            }
        }
    }, [rok]);

    useEffect(() => {
        loadOverview();
    }, [loadOverview]);

    const handleYearChange = (delta) => {
        setRok((y) => y + delta);
    };

    const renderUserCard = (row) => {
        const isOpen = expandedId === row.user_id;
        const mesice = row.mesice || [];
        const celkemCerpano = mesice.reduce((s, m) => s + (Number(m.cerpano_h) || 0), 0);

        return (
            <div key={row.user_id} className="vacation-user-card">
                <button
                    type="button"
                    className={`vacation-user-header${isOpen ? ' open' : ''}`}
                    onClick={() => setExpandedId(isOpen ? null : row.user_id)}
                    aria-expanded={isOpen}
                >
                    <span className="vacation-user-name">{row.jmeno}</span>
                    <span className="vacation-user-summary">
                        zbývá <strong>{formatNumber(row.zbyva_h)} h</strong>
                        {' '}/ fond {formatNumber(row.fond_h)} h
                    </span>
                    <span className="vacation-expand-icon">{isOpen ? '▼' : '▶'}</span>
                </button>

                {isOpen && (
                    <div className="vacation-user-body">
                        <div className="vacation-stats-grid">
                            <div className="vacation-stat">
                                <div className="vacation-stat-value">{formatNumber(row.fond_h)} h</div>
                                <div className="vacation-stat-label">Roční fond</div>
                            </div>
                            <div className="vacation-stat">
                                <div className="vacation-stat-value">{formatNumber(row.cerpano_h)} h</div>
                                <div className="vacation-stat-label">Čerpáno celkem</div>
                            </div>
                            <div className="vacation-stat">
                                <div className="vacation-stat-value">{formatNumber(row.zbyva_h)} h</div>
                                <div className="vacation-stat-label">Zbývá</div>
                            </div>
                            <div className="vacation-stat highlight">
                                <div className="vacation-stat-value">
                                    {formatPoints(row.dovolena_sazba_h)}/h
                                </div>
                                <div className="vacation-stat-label">
                                    Sazba dovolené (výplata / h)
                                </div>
                            </div>
                        </div>

                        {(row.cerpano_smeny_h > 0 || row.odeceno_deficit_h > 0 || row.prevod_h > 0 || row.korekce_cerpano_h) && (
                            <div className="vacation-meta">
                                {row.cerpano_smeny_h > 0 && (
                                    <span>Směny dovolené: <strong>{formatNumber(row.cerpano_smeny_h)} h</strong></span>
                                )}
                                {row.odeceno_deficit_h > 0 && (
                                    <span>Deficit fondu: <strong>{formatNumber(row.odeceno_deficit_h)} h</strong></span>
                                )}
                                {row.korekce_cerpano_h ? (
                                    <span>Korekce (sync): <strong>{formatNumber(row.korekce_cerpano_h)} h</strong></span>
                                ) : null}
                                {row.prevod_h > 0 && (
                                    <span>Převod z minulého roku: <strong>{formatNumber(row.prevod_h)} h</strong></span>
                                )}
                            </div>
                        )}

                        <p className="vacation-rate-hint">
                            Průměr mzdy (jako ve výplatě, bez dopravného a dýška) za poslední 3 měsíce (k {row.prumer_mesice || `${rok}`}):
                            {' '}<strong>{formatPoints(row.prumer_fixni_h)} bodů/h</strong>
                            {' '}→ výplata dovolené {formatPoints(row.dovolena_sazba_h)} bodů/h
                        </p>

                        {row.prumer_detail?.mesice?.length > 0 && (
                            <div className="vacation-table-wrap">
                                <table className="vacation-table vacation-table--prumer">
                                    <thead>
                                        <tr>
                                            <th>Měsíc (průměr)</th>
                                            <th>Odpracováno</th>
                                            <th>Základ</th>
                                            <th>Provize</th>
                                            <th>Položky</th>
                                            <th>Odměna</th>
                                            <th>Srážky</th>
                                            <th>Sazba</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {row.prumer_detail.mesice.map((pm) => (
                                            <tr key={`${pm.rok}-${pm.mesic}`}>
                                                <td>{MONTH_NAMES[pm.mesic - 1]} {pm.rok}</td>
                                                <td>{formatNumber(pm.odpracovano_h)} h</td>
                                                <td>{formatPoints(pm.zaklad_body ?? pm.fixni_body)}</td>
                                                <td>{formatPoints(pm.provize_body || 0)}</td>
                                                <td>{formatPoints(pm.pol_dok_odmena_body || 0)}</td>
                                                <td>{formatPoints(pm.odmena_mesic_body || 0)}</td>
                                                <td>
                                                    {pm.penalizace_srazka_body > 0 && (
                                                        <span title="Srážky z provize">
                                                            −{formatPoints(pm.penalizace_srazka_body)}
                                                        </span>
                                                    )}
                                                    {!pm.penalizace_srazka_body && '—'}
                                                </td>
                                                <td>{formatPoints(pm.sazba_h)}/h</td>
                                            </tr>
                                        ))}
                                    </tbody>
                                    <tfoot>
                                        <tr>
                                            <td>Celkem / průměr</td>
                                            <td>{formatNumber(row.prumer_detail.celkem_h)} h</td>
                                            <td>{formatPoints(row.prumer_detail.celkem_fixni)}</td>
                                            <td>{formatPoints(row.prumer_detail.celkem_provize || 0)}</td>
                                            <td>{formatPoints(row.prumer_detail.celkem_pol_dok || 0)}</td>
                                            <td>{formatPoints(row.prumer_detail.celkem_odmena || 0)}</td>
                                            <td>
                                                {row.prumer_detail.celkem_penalizace > 0 ? (
                                                    <span>−{formatPoints(row.prumer_detail.celkem_penalizace)}</span>
                                                ) : '—'}
                                            </td>
                                            <td><strong>{formatPoints(row.prumer_detail.prumer_fixni_h)}/h</strong></td>
                                        </tr>
                                    </tfoot>
                                </table>
                            </div>
                        )}

                        <div className="vacation-table-wrap">
                            <table className="vacation-table">
                                <thead>
                                    <tr>
                                        <th>Měsíc</th>
                                        <th>Směny dovolené</th>
                                        <th>Deficit fondu</th>
                                        <th>Čerpáno celkem</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {mesice.map((m) => (
                                        <tr key={m.mesic} className={m.cerpano_h > 0 ? 'has-usage' : ''}>
                                            <td>{MONTH_NAMES[m.mesic - 1]}</td>
                                            <td>{formatNumber(m.dovolena_smeny_h)} h</td>
                                            <td>
                                                {m.deficit_h > 0 && formatNumber(m.deficit_h)}
                                                {m.deficit_predikce_h > 0 && (
                                                    <span className="vacation-pending" title="Po skončení měsíce">
                                                        {formatNumber(m.deficit_predikce_h)} h*
                                                    </span>
                                                )}
                                                {!m.deficit_h && !m.deficit_predikce_h && '—'}
                                            </td>
                                            <td><strong>{formatNumber(m.cerpano_h)} h</strong></td>
                                        </tr>
                                    ))}
                                </tbody>
                                <tfoot>
                                    <tr>
                                        <td colSpan={3}>Součet čerpání v roce</td>
                                        <td><strong>{formatNumber(celkemCerpano)} h</strong></td>
                                    </tr>
                                </tfoot>
                            </table>
                        </div>
                        {mesice.some((m) => m.deficit_predikce_h > 0) && (
                            <p className="vacation-footnote">* Předpokládaný deficit – odečte se po skončení měsíce</p>
                        )}
                    </div>
                )}
            </div>
        );
    };

    if (loading && users.length === 0) {
        return <div className="vacation-panel loading">Načítání dovolené…</div>;
    }

    return (
        <div className="vacation-panel">
            <div className="vacation-header">
                <div className="year-navigation">
                    <button type="button" onClick={() => handleYearChange(-1)} title="Předchozí rok">
                        ◀
                    </button>
                    <h3>{rok}</h3>
                    <button type="button" onClick={() => handleYearChange(1)} title="Následující rok">
                        ▶
                    </button>
                </div>
            </div>

            {error && <div className="error-message">{error}</div>}

            {!eligible && (
                <p className="vacation-ineligible">{message || 'Fond dovolené se nevztahuje na tuto roli.'}</p>
            )}

            {eligible && users.length === 0 && !loading && (
                <p className="vacation-empty">Žádní zaměstnanci s nárokem na dovolenou.</p>
            )}

            <div className="vacation-users">
                {users.map(renderUserCard)}
            </div>
        </div>
    );
}

export default VacationPanel;
