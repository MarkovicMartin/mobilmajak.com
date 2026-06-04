import React from 'react';
import { POLOZKY_SELLER_DETAIL_ITEMS } from '../sections/polozkySellerDetail';

const PolozkySellerDetailChips = ({ item, losPctFn, dense = false }) => (
    <div className={`seller-detail-chips${dense ? ' seller-detail-chips--dense' : ''}`}>
        {POLOZKY_SELLER_DETAIL_ITEMS.map((def) => {
            const value = def.format(item);
            const extra = def.extra?.(item, losPctFn);
            const title = typeof def.title === 'function' ? def.title(item) : def.title;
            const isZero = value === 0
                || value === '0'
                || (typeof value === 'string' && /^0\s*Kč$/i.test(String(value).trim()));
            return (
                <div
                    key={def.key}
                    className={`polozky-chip${def.className ? ` ${def.className}` : ''}${isZero ? ' polozky-chip--zero' : ''}`}
                    title={title || def.label}
                >
                    <span className="polozky-chip__value">{value}</span>
                    <span className="polozky-chip__label">{def.label}</span>
                    {extra != null && (
                        <span className="polozky-chip__extra">{extra}</span>
                    )}
                </div>
            );
        })}
    </div>
);

export default PolozkySellerDetailChips;
