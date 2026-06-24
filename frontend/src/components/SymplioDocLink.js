import React from 'react';

const SYMPLIO_ADMIN = 'https://www.mobilmajak.cz/admin';

export function symplioDokladPdfUrl(doklad) {
    if (!doklad) return null;
    const text = String(doklad).trim();
    if (!text) return null;
    return `${SYMPLIO_ADMIN}/doklad-${encodeURIComponent(text)}.pdf?akce=open`;
}

export default function SymplioDocLink({
    doklad,
    url,
    label,
    className,
    title,
}) {
    const href = url || symplioDokladPdfUrl(doklad);
    const text = label ?? doklad;
    if (!href || !text) return text || '—';
    return (
        <a
            href={href}
            target="_blank"
            rel="noopener noreferrer"
            className={className || 'symplio-doc-link'}
            title={title || 'Otevřít doklad v Sympliu (PDF)'}
            onClick={(e) => e.stopPropagation()}
        >
            {text}
        </a>
    );
}
