import React from 'react';
import './BrandLogoMark.css';

/**
 * Symbol „A“ (maják) z CI 2017 – plnobarevná / inverzní varianta přes CSS tokeny.
 */
export default function BrandLogoMark({ className = '', title = 'MOBIL MAJÁK' }) {
    return (
        <svg
            className={`brand-logo-mark ${className}`.trim()}
            viewBox="0 0 100 140"
            role="img"
            aria-label={title}
            xmlns="http://www.w3.org/2000/svg"
        >
            <title>{title}</title>
            <rect className="brand-logo-mark__beacon" x="39" y="4" width="22" height="32" rx="11" />
            <path
                className="brand-logo-mark__a"
                fillRule="evenodd"
                d="M8 140Q4 140 4 134V128L38 44h24l34 84v6l-6 6H8Zm42-62L37 116h26L50 78Z"
            />
        </svg>
    );
}
