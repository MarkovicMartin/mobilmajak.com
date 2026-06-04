import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { format } from 'date-fns';
import { cs } from 'date-fns/locale';
import { shiftsAPI } from '../services/api';
import CameraBeacon from './CameraBeacon';

const STATUS_CLASS = {
    ok: 'work-tile--ok',
    partial: 'work-tile--partial',
    absent: 'work-tile--absent',
    no_shift: 'work-tile--absent',
};

function personLine(person) {
    switch (person.status) {
        case 'present':
            return {
                nameClass: 'work-person--present',
                meta: person.cas ? `v práci · příchod ${person.cas}` : 'v práci',
            };
        case 'upcoming':
            return {
                nameClass: 'work-person--upcoming',
                meta: `očekáván od ${person.plan_od}`,
            };
        case 'missing':
            return {
                nameClass: 'work-person--missing',
                meta: `chybí příchod (od ${person.plan_od})`,
            };
        case 'left':
            return {
                nameClass: 'work-person--left',
                meta: person.cas ? `odešel ${person.cas}` : 'odešel',
            };
        default:
            return { nameClass: '', meta: '' };
    }
}

export default function TodayWorkBoard({ today = new Date() }) {
    const navigate = useNavigate();
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    const load = useCallback(async () => {
        try {
            const json = await shiftsAPI.getTodayWorkBoard();
            setData(json);
            setError('');
        } catch (e) {
            setError(e.message || 'Chyba při načítání docházky');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        load();
        const id = setInterval(load, 45000);
        return () => clearInterval(id);
    }, [load]);

    const stores = data?.stores || [];
    const storeCount = stores.length;

    const openAbsentStores = () => {
        navigate('/shifts', { state: { view: 'absent-stores' } });
    };

    const formatCheckedAt = (iso) => {
        if (!iso) return '';
        return new Date(iso).toLocaleTimeString('cs-CZ', {
            hour: '2-digit',
            minute: '2-digit',
        });
    };

    return (
        <section className="work-board-section" aria-labelledby="work-board-heading">
            <div className="work-board-header">
                <div>
                    <h3 id="work-board-heading" className="work-board-title">
                        Kdo je dnes v práci
                    </h3>
                    {data?.checked_at && (
                        <p className="work-board-checked">
                            Aktualizace {formatCheckedAt(data.checked_at)}
                        </p>
                    )}
                </div>
                <div className="work-board-meta">
                    <span className="badge badge--minimal">
                        {format(today, 'd. MMM', { locale: cs })}
                    </span>
                    {storeCount > 0 && (
                        <span className="shifts-count-pill">{storeCount} prodejen</span>
                    )}
                    <button type="button" className="btn-secondary-sm" onClick={load}>
                        ↻
                    </button>
                </div>
            </div>

            {error && <div className="error-message">{error}</div>}

            {loading && !data ? (
                <div className="work-board-loading muted">Načítám stavy docházky…</div>
            ) : storeCount === 0 ? (
                <div className="work-board-empty muted">Dnes žádné naplánované směny</div>
            ) : (
                <div className="work-board-grid">
                    {stores.map((store) => (
                        <button
                            key={store.prodejna_id}
                            type="button"
                            className={`work-tile ${STATUS_CLASS[store.status] || ''}`}
                            style={{ borderLeftColor: store.prodejna_barva }}
                            onClick={openAbsentStores}
                        >
                            <div className="work-tile-head">
                                <span className="work-tile-store">{store.prodejna_nazev}</span>
                                <CameraBeacon camera={store.camera} />
                            </div>
                            {store.people.length === 0 ? (
                                <p className="work-tile-empty-msg">
                                    {store.message || 'Není směna · není příchod'}
                                </p>
                            ) : (
                                <ul className="work-tile-people">
                                    {store.people.map((person) => {
                                        const line = personLine(person);
                                        return (
                                            <li key={person.smena_id} className="work-person">
                                                <span className={`work-person-name ${line.nameClass}`}>
                                                    {person.jmeno}
                                                </span>
                                                <span className="work-person-meta">{line.meta}</span>
                                            </li>
                                        );
                                    })}
                                </ul>
                            )}
                        </button>
                    ))}
                </div>
            )}
        </section>
    );
}
