import React, { useEffect, useRef, useState } from 'react';
import '../../../components/CustomDropdown.css';

export const POLOZKY_METRIC_GROUPS = [
    {
        id: 'core',
        label: 'Hlavní KPI',
        metrics: [
            { key: 'polozky_nad_100', label: 'Položky nad 100 Kč' },
            { key: 'sluzby_celkem', label: 'Služby celkem' },
            { key: 'sunshine', label: 'Sunshine' },
            { key: 'unikatni_doklady', label: 'Unikátní doklady' },
            { key: 'pol_dok', label: 'Průměr pol./účt.' },
            { key: 'celkovy_obrat', label: 'Obrat s DPH' },
        ],
    },
    {
        id: 'services',
        label: 'Služby (kódy)',
        metrics: [
            { key: 'ct300', label: 'CT300' },
            { key: 'ct600', label: 'CT600' },
            { key: 'ct1200', label: 'CT1200' },
            { key: 'akt', label: 'AKT' },
            { key: 'zah250', label: 'ZAH250' },
            { key: 'nap', label: 'NAP' },
            { key: 'zah500', label: 'ZAH500' },
            { key: 'kop250', label: 'KOP250' },
            { key: 'kop500', label: 'KOP500' },
            { key: 'pz1', label: 'PZ1' },
            { key: 'knz', label: 'KNZ' },
            { key: 'sklicka', label: 'Skla / fólie' },
            { key: 'lepeni', label: 'LOS' },
            { key: 'vykupy', label: 'Výkup' },
            { key: 'viceprace_obrat', label: 'Vícepráce' },
        ],
    },
    {
        id: 'plan',
        label: 'Plánovací kategorie',
        metrics: [
            { key: 'NOVE_TELEFONY', label: 'Nové telefony' },
            { key: 'BAZAROVE_TELEFONY', label: 'Bazarové telefony' },
            { key: 'PRISLUSENSTVI_SKLA', label: 'Přísl. skla' },
            { key: 'PRISLUSENSTVI_OBALY', label: 'Přísl. obaly' },
            { key: 'SLUZBY', label: 'Služby (kat.)' },
            { key: 'SERVIS', label: 'Servis (kat.)' },
        ],
    },
    {
        id: 'hourly',
        label: 'Za hodinu',
        metrics: [
            { key: 'odpracovane_hodiny', label: 'Odpracované hodiny' },
            { key: 'polozky_nad_100_za_hodinu', label: 'Položky / hod' },
            { key: 'celkovy_obrat_za_hodinu', label: 'Obrat / hod' },
        ],
    },
];

export const ALL_POLOZKY_METRIC_KEYS = POLOZKY_METRIC_GROUPS.flatMap((g) => g.metrics.map((m) => m.key));

export const DEFAULT_VISIBLE_METRICS = new Set(ALL_POLOZKY_METRIC_KEYS);

const triggerLabel = (visibleMetrics) => {
    const n = visibleMetrics.size;
    const total = ALL_POLOZKY_METRIC_KEYS.length;
    if (n === 0) return 'Vyberte metriky';
    if (n >= total) return 'Vše';
    return `${n} z ${total} metrik`;
};

const PolozkyMetricPicker = ({ visibleMetrics, onChange, className = '' }) => {
    const [isOpen, setIsOpen] = useState(false);
    const dropdownRef = useRef(null);

    useEffect(() => {
        const handleClickOutside = (event) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
                setIsOpen(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const allSelected = visibleMetrics.size >= ALL_POLOZKY_METRIC_KEYS.length;

    const setAll = (on) => {
        onChange(on ? new Set(ALL_POLOZKY_METRIC_KEYS) : new Set());
    };

    const toggle = (key) => {
        const next = new Set(visibleMetrics);
        if (next.has(key)) next.delete(key);
        else next.add(key);
        onChange(next);
    };

    return (
        <div className={`filter-group polozky-metric-dropdown ${className}`} ref={dropdownRef}>
            <label>Metriky:</label>
            <div className={`custom-dropdown polozky-metric-dropdown__control${isOpen ? ' is-open' : ''}`}>
                <button
                    type="button"
                    className={`dropdown-trigger${isOpen ? ' open' : ''}`}
                    onClick={() => setIsOpen((v) => !v)}
                    aria-expanded={isOpen}
                >
                    <span className="dropdown-value">{triggerLabel(visibleMetrics)}</span>
                    <span className={`dropdown-arrow${isOpen ? ' open' : ''}`}>▼</span>
                </button>
                {isOpen && (
                    <div className="dropdown-menu polozky-metric-dropdown__panel">
                        <label className="polozky-metric-dropdown__all">
                            <input
                                type="checkbox"
                                checked={allSelected}
                                onChange={(e) => setAll(e.target.checked)}
                            />
                            <span>Vše</span>
                        </label>
                        {POLOZKY_METRIC_GROUPS.map((group) => (
                            <div key={group.id} className="polozky-metric-dropdown__group">
                                <div className="polozky-metric-dropdown__group-title">{group.label}</div>
                                {group.metrics.map((m) => (
                                    <label key={m.key} className="polozky-metric-dropdown__item">
                                        <input
                                            type="checkbox"
                                            checked={visibleMetrics.has(m.key)}
                                            onChange={() => toggle(m.key)}
                                        />
                                        <span>{m.label}</span>
                                    </label>
                                ))}
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
};

export default PolozkyMetricPicker;
