import React from 'react';
import { PolozkyDeltaBadge } from './PolozkyComparisonDelta';
import { POLOZKY_METRIC_GROUPS } from './PolozkyMetricPicker';

const CORE_COMPARE_KEYS = [
    { key: 'polozky_nad_100', label: 'Položky nad 100 Kč' },
    { key: 'sluzby_celkem', label: 'Služby' },
    { key: 'unikatni_doklady', label: 'Unikátní doklady' },
    { key: 'pol_dok', label: 'Průměr pol./účt.' },
    { key: 'celkovy_obrat', label: 'Obrat s DPH' },
    { key: 'odpracovane_hodiny', label: 'Hodiny' },
    { key: 'polozky_nad_100_za_hodinu', label: 'Položky / hod' },
    { key: 'marze_vytvorena_za_hodinu', label: 'Marže / hod' },
];

const PolozkySellerCompare = ({ rows, visibleMetrics, compareUserA, compareUserB }) => {
    if (!compareUserA || !compareUserB) {
        return (
            <p className="polozky-chart-hint">Vyberte oba prodejce pro porovnání.</p>
        );
    }

    const rowA = rows.find((r) => String(r.id_prodejce) === String(compareUserA));
    const rowB = rows.find((r) => String(r.id_prodejce) === String(compareUserB));

    if (!rowA && !rowB) {
        return <p className="polozky-chart-hint">Pro vybrané prodejce nejsou v období data.</p>;
    }

    const metricKeys = CORE_COMPARE_KEYS.filter((m) => {
        if (!visibleMetrics || visibleMetrics.size === 0) return true;
        return visibleMetrics.has(m.key);
    });

    const extraServiceKeys = POLOZKY_METRIC_GROUPS.find((g) => g.id === 'services')?.metrics
        .filter((m) => visibleMetrics?.has(m.key))
        .map((m) => ({ key: m.key, label: m.label })) || [];

    const allKeys = [...metricKeys, ...extraServiceKeys];

    return (
        <div className="polozky-seller-compare">
            <h4>Porovnání prodejců (stejné období)</h4>
            <div className="polozky-seller-compare-table-wrap">
                <table className="polozky-seller-compare-table">
                    <thead>
                        <tr>
                            <th>Metrika</th>
                            <th>{rowA?.prodejce || `ID ${compareUserA}`}</th>
                            <th>{rowB?.prodejce || `ID ${compareUserB}`}</th>
                            <th>A → B</th>
                        </tr>
                    </thead>
                    <tbody>
                        {allKeys.map(({ key, label }) => {
                            const va = rowA?.[key];
                            const vb = rowB?.[key];
                            return (
                                <tr key={key}>
                                    <td>{label}</td>
                                    <td>{va ?? '—'}</td>
                                    <td>{vb ?? '—'}</td>
                                    <td>
                                        {rowA && rowB && (
                                            <PolozkyDeltaBadge left={va} right={vb} />
                                        )}
                                    </td>
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

export default PolozkySellerCompare;
