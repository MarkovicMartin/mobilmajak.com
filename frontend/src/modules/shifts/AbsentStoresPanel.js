import React, { useState, useEffect, useCallback } from 'react';
import './AbsentStoresPanel.css';

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

    const formatCheckedAt = (iso) => {
        if (!iso) return '';
        return new Date(iso).toLocaleString('cs-CZ', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
        });
    };

    if (loading && !data) {
        return <div className="absent-stores loading">Načítám přehled…</div>;
    }

    const absent = data?.absent_stores || [];
    const okStores = data?.ok_stores || [];
    const camera = data?.camera;

    return (
        <div className="absent-stores">
            <div className="absent-stores-toolbar">
                <div>
                    <h3>🚨 Není v práci</h3>
                    <p className="absent-stores-sub">
                        Prodejny s právě běžící směnou, kde chybí zakliknutý <strong>příchod</strong>.
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
                <div className="camera-planned-card">
                    <strong>{camera.label}</strong>
                    <p>{camera.hint}</p>
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
                            {camera.nvr_access.where_to_get_credentials?.length > 0 && (
                                <ul className="camera-nvr-creds">
                                    {camera.nvr_access.where_to_get_credentials.map((line, i) => (
                                        <li key={i}>{line}</li>
                                    ))}
                                </ul>
                            )}
                        </details>
                    )}
                </div>
            )}

            {absent.length === 0 ? (
                <div className="absent-all-ok" role="status">
                    ✓ Na všech prodejnách s aktuální směnou je někdo v práci (nebo nikdo nemá právě směnu).
                    {okStores.length > 0 && (
                        <span className="absent-ok-count"> Obsazeno: {okStores.length} prodejen.</span>
                    )}
                </div>
            ) : (
                <div className="absent-stores-grid">
                    {absent.map((store) => (
                        <div
                            key={store.prodejna_id}
                            className="absent-store-card"
                            style={{ borderLeftColor: store.prodejna_barva || '#ef4444' }}
                        >
                            <h4>{store.prodejna_nazev}</h4>
                            <p className="absent-store-meta">
                                {store.missing_shifts.length}{' '}
                                {store.missing_shifts.length === 1
                                    ? 'směna bez příchodu'
                                    : store.missing_shifts.length < 5
                                        ? 'směny bez příchodu'
                                        : 'směn bez příchodu'}
                            </p>
                            <ul className="absent-shift-list">
                                {store.missing_shifts.map((s) => (
                                    <li key={s.smena_id}>
                                        <span className="absent-name">{s.jmeno}</span>
                                        <span className="absent-plan">
                                            {s.plan_od}–{s.plan_do}
                                        </span>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    ))}
                </div>
            )}

            {okStores.length > 0 && (
                <details className="absent-ok-details">
                    <summary>V pořádku ({okStores.length} prodejen)</summary>
                    <ul className="absent-ok-list">
                        {okStores.map((store) => (
                            <li key={store.prodejna_id}>
                                <span
                                    className="absent-ok-dot"
                                    style={{ backgroundColor: store.prodejna_barva || '#22c55e' }}
                                />
                                {store.prodejna_nazev}
                                {' — '}
                                {store.present_shifts.map((s) => s.jmeno).join(', ')}
                            </li>
                        ))}
                    </ul>
                </details>
            )}
        </div>
    );
}

export default AbsentStoresPanel;
