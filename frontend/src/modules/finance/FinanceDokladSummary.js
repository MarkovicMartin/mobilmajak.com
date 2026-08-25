import React from 'react';
import './FinanceDokladSummary.css';

const formatCurrency = (value) => {
    if (value == null || value === '') return null;
    const n = Number(value);
    if (Number.isNaN(n)) return String(value);
    return new Intl.NumberFormat('cs-CZ', {
        style: 'currency',
        currency: 'CZK',
        minimumFractionDigits: 0,
        maximumFractionDigits: 2,
    }).format(n);
};

/**
 * Po nahrání FA: místo „Přidat doklad“ ukáže soubor + OCR pole.
 */
const FinanceDokladSummary = ({ doklad, compact = false }) => {
    if (!doklad) return null;

    const fileLabel = doklad.soubor_nazev || 'Soubor faktury';
    const parts = [];
    if (doklad.dodavatel_nazev) parts.push(doklad.dodavatel_nazev);
    if (doklad.cislo_faktury) parts.push(`FA ${doklad.cislo_faktury}`);
    if (doklad.vs) parts.push(`VS ${doklad.vs}`);
    const zaklad = formatCurrency(doklad.castka_bez_dph);
    const dph = formatCurrency(doklad.dph_castka);
    const celkem = formatCurrency(doklad.castka_celkem);
    if (zaklad) parts.push(`základ ${zaklad}`);
    if (dph) parts.push(`DPH ${dph}${doklad.dph_sazba ? ` (${doklad.dph_sazba} %)` : ''}`);
    if (celkem && !zaklad) parts.push(celkem);
    else if (celkem && zaklad) parts.push(`celkem ${celkem}`);

    return (
        <div className={`finance-doklad-summary${compact ? ' finance-doklad-summary--compact' : ''}`}>
            <div className="finance-doklad-summary__head">
                <span className="finance-badge finance-badge--ok">FA nahrána</span>
                {doklad.soubor_url ? (
                    <a href={doklad.soubor_url} target="_blank" rel="noopener noreferrer">
                        {fileLabel}
                    </a>
                ) : (
                    <span>{fileLabel}</span>
                )}
            </div>
            {parts.length > 0 && (
                <p className="finance-doklad-summary__meta">{parts.join(' · ')}</p>
            )}
            {!compact && !parts.length && (
                <p className="finance-doklad-summary__meta muted">OCR zatím nevyčetlo pole – zkontrolujte v Kontrole FA.</p>
            )}
        </div>
    );
};

export default FinanceDokladSummary;
