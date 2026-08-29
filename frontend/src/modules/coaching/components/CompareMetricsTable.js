import React from 'react';
import { formatCompareValue } from './CompareRateToggle';

const CompareMetricsTable = ({
    metriky = [],
    kategorie = [],
    nameA,
    nameB,
    mesicLabel,
    rateMode = 'total',
}) => {
    if (!metriky.length && !kategorie.length) return null;

    return (
        <>
            {metriky.length > 0 && (
                <table className="coaching-compare-table">
                    <thead>
                        <tr>
                            <th>{mesicLabel ? `Metrika (${mesicLabel})` : 'Metrika'}</th>
                            <th>{nameA}</th>
                            <th>{nameB}</th>
                        </tr>
                    </thead>
                    <tbody>
                        {metriky.map((row) => (
                            <tr key={row.metric} className={row.is_hours ? 'coaching-compare-row--hours' : undefined}>
                                <td>{row.label}</td>
                                <td>
                                    {formatCompareValue(row.a, row.a_za_hodinu, rateMode, {
                                        isHours: row.is_hours,
                                    })}
                                </td>
                                <td>
                                    {formatCompareValue(row.b, row.b_za_hodinu, rateMode, {
                                        isHours: row.is_hours,
                                    })}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            )}

            {kategorie.length > 0 && (
                <>
                    <h4>Kategorie v měsíci</h4>
                    <table className="coaching-compare-table">
                        <thead>
                            <tr>
                                <th>Kategorie</th>
                                <th>{nameA}</th>
                                <th>{nameB}</th>
                            </tr>
                        </thead>
                        <tbody>
                            {kategorie.map((row) => (
                                <tr key={row.kategorie_kod}>
                                    <td>{row.nazev}</td>
                                    <td>
                                        {formatCompareValue(row.a_kusy, row.a_kusy_za_hodinu, rateMode)}
                                        {rateMode === 'total' ? ' ks' : rateMode === 'per_hour' ? ' ks/h' : ''}
                                    </td>
                                    <td>
                                        {formatCompareValue(row.b_kusy, row.b_kusy_za_hodinu, rateMode)}
                                        {rateMode === 'total' ? ' ks' : rateMode === 'per_hour' ? ' ks/h' : ''}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </>
            )}
        </>
    );
};

export default CompareMetricsTable;
