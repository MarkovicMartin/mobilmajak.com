import React from 'react';
import BrandLogoMark from './BrandLogoMark';
import './ShellBrand.css';

/**
 * Značka v menu – symbol A + wordmark podle CI 2017 (FreightSans → Open Sans Bold).
 */
export default function ShellBrand({ showWordmark = true, className = '' }) {
    return (
        <div className={`shell-brand ${className}`.trim()}>
            <BrandLogoMark className="shell-brand__mark" />
            {showWordmark && <h1 className="shell-brand__wordmark">MOBIL MAJÁK</h1>}
        </div>
    );
}
