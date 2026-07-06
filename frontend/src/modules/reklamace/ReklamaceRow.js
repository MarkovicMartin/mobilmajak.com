import React, { useState } from 'react';
import {
    REKLAMACE_STATUS,
    ZPUSOB_VYRIzeni_OPTIONS,
    getRowStatusClass,
    getStatusLabel,
} from './constants';
import './ReklamaceRow.css';

const formatDate = (d) => {
    if (!d) return '—';
    return new Date(d).toLocaleDateString('cs-CZ');
};

const ReklamaceRow = ({
    item,
    onEdit,
    onDelete,
    onOdeslat,
    onPotvrdit,
    busy,
}) => {
    const [zpusob, setZpusob] = useState('vymena');
    const [showResolve, setShowResolve] = useState(false);

    const statusClass = getRowStatusClass(item);
    const statusLabel = getStatusLabel(item);

    const handlePotvrdit = () => {
        if (!zpusob) return;
        onPotvrdit(item.id, { zpusob_vyrizeni: zpusob });
        setShowResolve(false);
    };

    return (
        <article className={`reklamace-row ${statusClass}`}>
            <div className="reklamace-row__head">
                <span className="reklamace-row__znacka">{item.nase_znacka}</span>
                <span className="reklamace-row__status">{statusLabel}</span>
                <span className="reklamace-row__prodejna">{item.prodejna}</span>
                <span className="reklamace-row__datum">{formatDate(item.datum_odeslani)}</span>
                <div className="reklamace-row__actions">
                    <button type="button" className="btn-icon" onClick={onEdit} title="Upravit">
                        <i className="fas fa-pen" />
                    </button>
                    <button type="button" className="btn-icon btn-icon--danger" onClick={onDelete} title="Smazat">
                        <i className="fas fa-trash" />
                    </button>
                </div>
            </div>
            <div className="reklamace-row__title">{item.nazev_zbozi}</div>
            <div className="reklamace-row__meta">
                <span title="Dodavatel"><i className="fas fa-truck" /> {item.dodavatel || '—'}</span>
                <span title="Faktura"><i className="fas fa-file-invoice" /> {item.faktura || '—'}</span>
                <span title="EAN"><i className="fas fa-barcode" /> {item.ean || '—'}</span>
                <span title="P kód">P {item.p_kod || '—'}</span>
                <span title="Zásilka"><i className="fas fa-box" /> {item.cislo_zasilky || '—'}</span>
                {item.zpusob_vyrizeni_label && (
                    <span title="Způsob vyřízení"><i className="fas fa-check" /> {item.zpusob_vyrizeni_label}</span>
                )}
            </div>
            {item.poznamka && <div className="reklamace-row__note">{item.poznamka}</div>}

            <div className="reklamace-row__workflow">
                {item.status === REKLAMACE_STATUS.NEZPRACOVANE && (
                    <button
                        type="button"
                        className="btn btn-sm btn-warning"
                        disabled={busy}
                        onClick={() => onOdeslat(item.id)}
                    >
                        <i className="fas fa-paper-plane" /> Odeslat dodavateli
                    </button>
                )}
                {item.status === REKLAMACE_STATUS.ODESLANE && !showResolve && (
                    <button
                        type="button"
                        className="btn btn-sm btn-success"
                        disabled={busy}
                        onClick={() => setShowResolve(true)}
                    >
                        <i className="fas fa-check" /> Potvrdit zpracování
                    </button>
                )}
                {showResolve && (
                    <div className="reklamace-row__resolve">
                        <select
                            className="form-control"
                            value={zpusob}
                            onChange={(e) => setZpusob(e.target.value)}
                        >
                            {ZPUSOB_VYRIzeni_OPTIONS.map((o) => (
                                <option key={o.value} value={o.value}>{o.label}</option>
                            ))}
                        </select>
                        <button
                            type="button"
                            className="btn btn-sm btn-success"
                            disabled={busy}
                            onClick={handlePotvrdit}
                        >
                            Potvrdit
                        </button>
                        <button
                            type="button"
                            className="btn btn-sm btn-outline"
                            disabled={busy}
                            onClick={() => setShowResolve(false)}
                        >
                            Zrušit
                        </button>
                    </div>
                )}
            </div>
        </article>
    );
};

export default ReklamaceRow;
