import React, { useState, useEffect, useCallback } from 'react';
import CameraBeacon from '../../components/CameraBeacon';
import { formatPragueClock, formatPragueEventAt } from '../../utils/pragueDateTime';
import './AbsentStoresPanel.css';

function motionToCamera(motion) {
    if (!motion?.in_pilot) return null;
    return {
        in_pilot: true,
        active: motion.status === 'active',
    };
}

function AbsentStoresPanel() {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    const load = useCallback(async () => {
        try {
            const res = await fetch('/api/shifts/attendance/absent-stores/', { credentials: 'include' });
            if (!res.ok) {
                const body = await res.json().catch(() => ({}));
                throw new Error(body.error || 'Chyba při načítání');
            }
            const json = await res.json();
            setData(json);
            setError('');
        } catch (e) {
            setError(e.message);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        load();
        const id = setInterval(load, 45000);
        return () => clearInterval(id);
    }, [load]);

    const formatCheckedAt = (iso) => formatPragueClock(iso);

    const motionBeacon = (motion) => {
        const camera = motionToCamera(motion);
        if (!camera) return null;
        const lastAt = motion.last_event_at ? formatPragueEventAt(motion.last_event_at) : '';
        const title = lastAt ? `Poslední signál: ${lastAt}` : undefined;
        return (
            <span className="store-motion-row">
                <CameraBeacon camera={camera} title={title} />
                <span
                    className={`motion-label motion-label--${motion.status || 'unknown'}`}
                >
                    {motion.label}
                </span>
            </span>
        );
    };

    const renderCameraEvents = (store) => {
        if (!store.motion?.in_pilot) return null;
        const events = store.recent_events || [];
        if (events.length === 0) {
            return <p className="store-camera-empty">Zatím žádné signály z brány.</p>;
        }
        return (
            <ul className="store-camera-events">
                {events.map((ev) => (
                    <li key={ev.id}>
                        {formatPragueEventAt(ev.cas)} — {ev.pohyb ? 'pohyb' : 'klid'}
                        {ev.zdroj ? ` (${ev.zdroj})` : ''}
                    </li>
                ))}
            </ul>
        );
    };

    if (loading && !data) {
        return <div className="absent-stores loading">Načítám přehled…</div>;
    }

    const absent = data?.absent_stores || [];
    const okStores = data?.ok_stores || [];
    const pilotStores = data?.pilot_stores || [];
    const camera = data?.camera;

    const activeIds = new Set([
        ...absent.map((s) => s.prodejna_id),
        ...okStores.map((s) => s.prodejna_id),
    ]);
    const pilotOnly = pilotStores.filter((s) => !activeIds.has(s.prodejna_id));

    const resolveStoreStatus = (store) => {
        if (store.status === 'ok' || store.status === 'partial' || store.status === 'absent') {
            return store.status;
        }
        const present = (store.present_shifts || []).length;
        const missing = (store.missing_shifts || []).length;
        if (present > 0 && missing === 0) return 'ok';
        if (present > 0 && missing > 0) return 'partial';
        return 'absent';
    };

    const allActive = [
        ...absent,
        ...okStores,
    ]
        .map((store) => ({ ...store, attendanceStatus: resolveStoreStatus(store) }))
        .sort((a, b) => a.prodejna_nazev.localeCompare(b.prodejna_nazev, 'cs'));

    const statusPill = (status) => {
        if (status === 'ok') return { className: 'pill-ok', label: '✓ V pořádku' };
        if (status === 'partial') return { className: 'pill-partial', label: '⚠ Chybí část týmu' };
        return { className: 'pill-absent', label: '⚠ Chybí příchod' };
    };

    const renderShiftRoster = (store) => {
        const presentIds = new Set((store.present_shifts || []).map((s) => s.smena_id));
        const shifts = [...(store.active_shifts || [])].sort((a, b) => (
            (a.plan_od || '').localeCompare(b.plan_od || '')
        ));

        return (
            <ul className="store-shift-roster">
                {shifts.map((shift) => {
                    const isPresent = presentIds.has(shift.smena_id);
                    return (
                        <li
                            key={shift.smena_id}
                            className={isPresent ? 'shift-present' : 'shift-missing'}
                        >
                            <span className="shift-roster-name">{shift.jmeno}</span>
                            <span className="shift-roster-meta">
                                {shift.plan_od}–{shift.plan_do}
                                {isPresent && shift.prichod ? ` · příchod ${shift.prichod}` : ''}
                            </span>
                        </li>
                    );
                })}
            </ul>
        );
    };

    return (
        <div className="absent-stores">
            <div className="absent-stores-toolbar">
                <div>
                    <h3>🚨 Není v práci</h3>
                    <p className="absent-stores-sub">
                        Prodejny s právě běžící směnou. U každé dlaždice vidíte všechny lidi na směně – zelené jméno = v práci, červené = chybí příchod.
                        {data?.auto_close_time && (
                            <> Stav „v práci“ se po <strong>{data.auto_close_time}</strong> automaticky ukončí.</>
                        )}
                    </p>
                </div>
                <button type="button" className="btn-secondary-sm" onClick={load}>
                    ↻ Obnovit
                </button>
            </div>

            {data?.checked_at && (
                <p className="absent-checked-at">Kontrola: {formatCheckedAt(data.checked_at)}</p>
            )}

            {error && <div className="error-message">{error}</div>}

            {camera && (
                <div className={`camera-planned-card${camera.enabled ? ' camera-pilot-active' : ''}`}>
                    <strong>{camera.label}</strong>
                    <p>{camera.hint}</p>
                    {camera.enabled && camera.motion_window_minutes && (
                        <p className="camera-pilot-window">
                            Pohyb = událost za posledních {camera.motion_window_minutes} min (bez obrazu na serveru).
                        </p>
                    )}
                    {camera.nvr_access && (
                        <details className="camera-nvr-guide">
                            <summary>{camera.nvr_access.title}</summary>
                            {camera.nvr_access.note && <p className="camera-nvr-note">{camera.nvr_access.note}</p>}
                            {(camera.nvr_access.methods || []).map((m) => (
                                <div key={m.name} className="camera-nvr-method">
                                    <strong>{m.name}</strong>
                                    <ol>
                                        {(m.steps || []).map((step, i) => (
                                            <li key={i}>{step}</li>
                                        ))}
                                    </ol>
                                </div>
                            ))}
                        </details>
                    )}
                </div>
            )}

            {allActive.length === 0 ? (
                <div className="absent-all-ok" role="status">
                    ✓ Žádná prodejna nemá právě aktivní směnu.
                </div>
            ) : (
                <div className="absent-stores-grid">
                    {allActive.map((store) => {
                        const status = store.attendanceStatus;
                        const cardClass = status === 'ok'
                            ? 'store-attendance-ok'
                            : status === 'partial'
                                ? 'store-attendance-partial'
                                : 'store-attendance-absent';
                        const pill = statusPill(status);
                        const borderColor = store.prodejna_barva || (
                            status === 'ok' ? '#22c55e' : status === 'partial' ? '#f59e0b' : '#ef4444'
                        );

                        return (
                            <div
                                key={store.prodejna_id}
                                className={`store-attendance-card ${cardClass}`}
                                style={{ borderLeftColor: borderColor }}
                            >
                                <div className="store-attendance-head">
                                    <h4>{store.prodejna_nazev}</h4>
                                    <span className={`store-status-pill ${pill.className}`}>
                                        {pill.label}
                                    </span>
                                </div>

                                {motionBeacon(store.motion)}

                                {renderShiftRoster(store)}

                                {store.motion?.in_pilot && (
                                    <div className="store-camera-block">
                                        <strong className="store-camera-label">📷 Kamera</strong>
                                        {renderCameraEvents(store)}
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>
            )}

            {pilotOnly.length > 0 && (
                <div className="camera-pilot-stores">
                    <h4>📷 Pilot kamer – bez aktivní směny</h4>
                    <ul className="camera-pilot-list">
                        {pilotOnly.map((store) => (
                            <li key={store.prodejna_id} className="camera-pilot-item">
                                <div className="camera-pilot-head">
                                    <strong>{store.prodejna_nazev}</strong>
                                    {motionBeacon(store.motion)}
                                </div>
                                {renderCameraEvents(store)}
                            </li>
                        ))}
                    </ul>
                </div>
            )}
        </div>
    );
}

export default AbsentStoresPanel;
