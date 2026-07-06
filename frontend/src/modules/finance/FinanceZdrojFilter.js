import React from 'react';
import { ZDROJ_FILTERS, countByZdroj } from './financeUtils';

const FinanceZdrojFilter = ({ value, onChange, items }) => {
    const counts = countByZdroj(items);

    return (
        <div className="finance-filters" role="group" aria-label="Filtr zdroje">
            {ZDROJ_FILTERS.map((f) => {
                const count = f.id === 'fio'
                    ? counts.fio
                    : f.id === 'symplio_pokladna'
                        ? counts.kasa
                        : counts.all;
                const active = value === f.id;
                return (
                    <button
                        key={f.id || 'all'}
                        type="button"
                        className={`finance-filter-chip${active ? ' active' : ''}${f.id === 'fio' ? ' finance-filter-chip--fio' : ''}${f.id === 'symplio_pokladna' ? ' finance-filter-chip--kasa' : ''}`}
                        onClick={() => onChange(f.id)}
                    >
                        {f.label}
                        <span className="finance-filter-chip__count">{count}</span>
                    </button>
                );
            })}
        </div>
    );
};

export default FinanceZdrojFilter;
