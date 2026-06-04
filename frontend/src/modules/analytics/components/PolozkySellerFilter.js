import React, { useEffect, useRef, useState } from 'react';
import {
    SELLER_MODE_ALL,
    SELLER_MODE_COMPARE,
    SELLER_MODE_PICK,
    countPickedSellerIds,
    singlePickedSellerId,
} from '../sections/polozkyFilters';

const STAFF_ROLES = new Set(['PRODEJCE', 'VEDOUCI', 'BRIGADNIK']);

const sellerLabel = (u) => {
    const name = `${u.jmeno || ''} ${u.prijmeni || ''}`.trim();
    return name || `ID ${u.id}`;
};

const PolozkySellerFilter = ({
    scope,
    onChange,
    users = [],
    onSelfCompareInTime,
    className = '',
}) => {
    const [pickOpen, setPickOpen] = useState(false);
    const pickRef = useRef(null);
    const mode = scope.seller_mode || SELLER_MODE_ALL;

    const staffUsers = users.filter((u) => STAFF_ROLES.has(u.role));

    useEffect(() => {
        const handleClickOutside = (e) => {
            if (pickRef.current && !pickRef.current.contains(e.target)) setPickOpen(false);
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const pickedSet = new Set(
        (scope.user_ids || '').split(',').map((x) => x.trim()).filter(Boolean),
    );

    const togglePicked = (id) => {
        const sid = String(id);
        const next = new Set(pickedSet);
        if (next.has(sid)) next.delete(sid);
        else next.add(sid);
        onChange({
            seller_mode: SELLER_MODE_PICK,
            user_ids: [...next].join(','),
            compare_user_a: '',
            compare_user_b: '',
        });
    };

    const setMode = (seller_mode) => {
        if (seller_mode === SELLER_MODE_ALL) {
            onChange({
                seller_mode: SELLER_MODE_ALL,
                user_ids: '',
                compare_user_a: '',
                compare_user_b: '',
            });
            return;
        }
        if (seller_mode === SELLER_MODE_COMPARE) {
            onChange({
                seller_mode: SELLER_MODE_COMPARE,
                user_ids: '',
                compare_user_a: scope.compare_user_a || '',
                compare_user_b: scope.compare_user_b || '',
            });
            return;
        }
        onChange({
            seller_mode: SELLER_MODE_PICK,
            user_ids: scope.user_ids || '',
            compare_user_a: '',
            compare_user_b: '',
        });
    };

    const pickLabel = () => {
        const n = countPickedSellerIds(scope.user_ids);
        if (n === 0) return 'Vyberte prodejce';
        if (n === 1) {
            const id = singlePickedSellerId(scope);
            const u = staffUsers.find((x) => String(x.id) === id);
            return u ? sellerLabel(u) : `Prodejce ${id}`;
        }
        return `${n} prodejců`;
    };

    const oneId = singlePickedSellerId(scope);

    return (
        <div className={`polozky-seller-filter ${className}`}>
            <div className="filter-group">
                <label>Prodejci:</label>
                <select
                    value={mode}
                    onChange={(e) => setMode(e.target.value)}
                >
                    <option value={SELLER_MODE_ALL}>Všichni</option>
                    <option value={SELLER_MODE_PICK}>Konkrétní (jeden nebo více)</option>
                    <option value={SELLER_MODE_COMPARE}>Porovnat dva</option>
                </select>
            </div>

            {mode === SELLER_MODE_PICK && (
                <div className="filter-group polozky-seller-filter__pick" ref={pickRef}>
                    <label>Výběr:</label>
                    <div className={`custom-dropdown polozky-metric-dropdown__control${pickOpen ? ' is-open' : ''}`}>
                        <button
                            type="button"
                            className="dropdown-button"
                            onClick={() => setPickOpen((o) => !o)}
                            aria-expanded={pickOpen}
                        >
                            {pickLabel()}
                        </button>
                        {pickOpen && (
                            <div className="dropdown-menu polozky-metric-dropdown__panel polozky-seller-panel">
                                <button
                                    type="button"
                                    className="polozky-seller-panel__clear"
                                    onClick={() => onChange({
                                        seller_mode: SELLER_MODE_PICK,
                                        user_ids: '',
                                        compare_user_a: '',
                                        compare_user_b: '',
                                    })}
                                >
                                    Zrušit výběr
                                </button>
                                <div className="polozky-seller-list">
                                    {staffUsers.map((u) => {
                                        const sid = String(u.id);
                                        const on = pickedSet.has(sid);
                                        return (
                                            <label key={sid} className="polozky-metric-dropdown__item polozky-seller-option">
                                                <input
                                                    type="checkbox"
                                                    checked={on}
                                                    onChange={() => togglePicked(u.id)}
                                                />
                                                <span>{sellerLabel(u)}</span>
                                                <span className="polozky-seller-option-role">{u.role}</span>
                                            </label>
                                        );
                                    })}
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            )}

            {mode === SELLER_MODE_COMPARE && (
                <>
                    <div className="filter-group">
                        <label>Prodejce A:</label>
                        <select
                            value={scope.compare_user_a || ''}
                            onChange={(e) => onChange({
                                compare_user_a: e.target.value,
                                compare_user_b: scope.compare_user_b,
                            })}
                        >
                            <option value="">—</option>
                            {staffUsers.map((u) => (
                                <option key={u.id} value={u.id}>{sellerLabel(u)}</option>
                            ))}
                        </select>
                    </div>
                    <div className="filter-group">
                        <label>Prodejce B:</label>
                        <select
                            value={scope.compare_user_b || ''}
                            onChange={(e) => onChange({
                                compare_user_a: scope.compare_user_a,
                                compare_user_b: e.target.value,
                            })}
                        >
                            <option value="">—</option>
                            {staffUsers.map((u) => (
                                <option key={u.id} value={u.id}>{sellerLabel(u)}</option>
                            ))}
                        </select>
                    </div>
                </>
            )}

            {oneId && onSelfCompareInTime && (
                <div className="filter-group polozky-seller-filter__self">
                    <button
                        type="button"
                        className="polozky-self-time-btn"
                        onClick={() => onSelfCompareInTime(oneId)}
                        title="Zapne srovnání období vlevo/vpravo pro stejného prodejce"
                    >
                        Sám v čase
                    </button>
                </div>
            )}
        </div>
    );
};

export default PolozkySellerFilter;
