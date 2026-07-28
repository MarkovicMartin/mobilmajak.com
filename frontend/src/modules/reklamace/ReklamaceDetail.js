import React, { useState, useEffect, useMemo } from 'react';
import Modal from '../../components/Modal';
import {
    getMoveTargets,
    statusConfig,
    statusLabel,
    formatDateTime,
    promptZpusobVyrizeni,
    ZPUSOB_VYRIzeni_OPTIONS,
    REKLAMACE_STATUS,
} from './reklamaceHelpers';
import './ReklamaceDetail.css';

const emptyFieldsFromItem = (item) => ({
    nazev_zbozi: item.nazev_zbozi || '',
    jejich_oznaceni: item.jejich_oznaceni || '',
    dodavatel: item.dodavatel || '',
    faktura: item.faktura || '',
    ean: item.ean || '',
    p_kod: item.p_kod || '',
    datum_odeslani: item.datum_odeslani || '',
    cislo_zasilky: item.cislo_zasilky || '',
    poznamka: item.poznamka || '',
    prodejna: item.prodejna || '',
    zpusob_vyrizeni: item.zpusob_vyrizeni || '',
    datum_vyrizeni: item.datum_vyrizeni || '',
    sklad_vyskladneno: Boolean(item.sklad_vyskladneno),
    sklad_naskladneno: Boolean(item.sklad_naskladneno),
});

const ReklamaceDetail = ({ item, onClose, onDelete, onStatusChange, onUpdate }) => {
    const [currentStatus, setCurrentStatus] = useState(item.status);
    const [statusDisplay, setStatusDisplay] = useState(
        item.status_label || statusLabel(item.status),
    );
    const [fields, setFields] = useState(() => emptyFieldsFromItem(item));
    const [baseline, setBaseline] = useState(() => emptyFieldsFromItem(item));
    const [changingStatus, setChangingStatus] = useState(false);
    const [saving, setSaving] = useState(false);
    const [saveError, setSaveError] = useState('');

    useEffect(() => {
        setCurrentStatus(item.status);
        setStatusDisplay(item.status_label || statusLabel(item.status));
        const next = emptyFieldsFromItem(item);
        setFields(next);
        setBaseline(next);
        setSaveError('');
    }, [item]);

    const moveTargets = getMoveTargets(currentStatus);
    const currentStatusCfg = statusConfig(currentStatus);
    const detailTitle = [item.nase_znacka, fields.nazev_zbozi].filter(Boolean).join(' · ')
        || 'Reklamace';

    const dirty = useMemo(() => (
        Object.keys(baseline).some((key) => {
            if (typeof baseline[key] === 'boolean') {
                return Boolean(fields[key]) !== Boolean(baseline[key]);
            }
            return String(fields[key] ?? '') !== String(baseline[key] ?? '');
        })
    ), [fields, baseline]);

    const setField = (name, value) => {
        setFields((prev) => ({ ...prev, [name]: value }));
        setSaveError('');
    };

    const handleSave = async () => {
        if (!onUpdate || !dirty || saving) return;
        setSaving(true);
        setSaveError('');
        try {
            const patch = {};
            Object.keys(baseline).forEach((key) => {
                const changed = typeof baseline[key] === 'boolean'
                    ? Boolean(fields[key]) !== Boolean(baseline[key])
                    : String(fields[key] ?? '') !== String(baseline[key] ?? '');
                if (changed) {
                    if (key === 'datum_odeslani' || key === 'datum_vyrizeni') {
                        patch[key] = fields[key] || null;
                    } else {
                        patch[key] = fields[key];
                    }
                }
            });
            const result = await onUpdate(item.id, patch);
            if (result.success === false) {
                const err = result.error;
                const msg = typeof err === 'object'
                    ? (Object.values(err).flat?.()?.[0] || err.detail || JSON.stringify(err))
                    : (err || 'Uložení selhalo');
                setSaveError(typeof msg === 'string' ? msg : 'Uložení selhalo');
                return;
            }
            if (result.data) {
                const next = emptyFieldsFromItem(result.data);
                setFields(next);
                setBaseline(next);
            } else {
                setBaseline({ ...fields });
            }
        } catch {
            setSaveError('Uložení selhalo');
        } finally {
            setSaving(false);
        }
    };

    const handleMoveTo = async (newStatus) => {
        if (newStatus === currentStatus || changingStatus) return;

        let zpusob = null;
        if (newStatus === REKLAMACE_STATUS.VRIZENE) {
            zpusob = promptZpusobVyrizeni();
            if (!zpusob) {
                alert('Způsob vyřízení je povinný.');
                return;
            }
        }

        const prevStatus = currentStatus;
        const prevDisplay = statusDisplay;

        setChangingStatus(true);
        setCurrentStatus(newStatus);
        setStatusDisplay(statusLabel(newStatus));
        if (zpusob) {
            setFields((prev) => ({ ...prev, zpusob_vyrizeni: zpusob }));
            setBaseline((prev) => ({ ...prev, zpusob_vyrizeni: zpusob }));
        }

        try {
            const result = await onStatusChange(item.id, newStatus, { zpusob_vyrizeni: zpusob });
            if (!result.success) {
                setCurrentStatus(prevStatus);
                setStatusDisplay(prevDisplay);
                const err = result.error;
                const msg = typeof err === 'object'
                    ? (err.detail || err.error || JSON.stringify(err))
                    : err;
                alert(msg);
            }
        } catch {
            setCurrentStatus(prevStatus);
            setStatusDisplay(prevDisplay);
            alert('Nepodařilo se změnit stav');
        } finally {
            setChangingStatus(false);
        }
    };

    const field = (label, name, opts = {}) => (
        <label className="rk-detail-item rk-detail-item--field">
            <span className="label">{label}</span>
            {opts.multiline ? (
                <textarea
                    className="rk-detail-input"
                    rows={3}
                    value={fields[name]}
                    onChange={(e) => setField(name, e.target.value)}
                    placeholder={opts.placeholder || ''}
                />
            ) : opts.type === 'select' ? (
                <select
                    className="rk-detail-input"
                    value={fields[name]}
                    onChange={(e) => setField(name, e.target.value)}
                >
                    <option value="">—</option>
                    {opts.options.map((o) => (
                        <option key={o.value} value={o.value}>{o.label}</option>
                    ))}
                </select>
            ) : opts.type === 'checkbox' ? (
                <input
                    type="checkbox"
                    checked={Boolean(fields[name])}
                    onChange={(e) => setField(name, e.target.checked)}
                />
            ) : (
                <input
                    className="rk-detail-input"
                    type={opts.type || 'text'}
                    value={fields[name]}
                    onChange={(e) => setField(name, e.target.value)}
                    placeholder={opts.placeholder || ''}
                />
            )}
        </label>
    );

    return (
        <Modal
            title={detailTitle}
            onClose={onClose}
            size="md"
            bodyClassName="rk-detail-content"
            footer={(
                <>
                    <button type="button" className="btn-cancel" onClick={onClose}>
                        Zavřít
                    </button>
                    <button
                        type="button"
                        className="btn-submit"
                        disabled={!dirty || saving}
                        onClick={handleSave}
                    >
                        {saving ? 'Ukládám…' : 'Uložit'}
                    </button>
                </>
            )}
        >
            <div className="rk-detail-section rk-detail-section--move">
                <h3>Přesunout do</h3>
                {moveTargets.length === 0 ? (
                    <p className="rk-detail-hint">Žádný další přechod (už je vyřízeno).</p>
                ) : (
                    <div className="rk-status-move" role="group" aria-label="Přesun stavu">
                        {moveTargets.map((col) => (
                            <button
                                key={col.key}
                                type="button"
                                className="rk-status-move__btn"
                                style={{
                                    backgroundColor: col.color,
                                    color: col.textColor,
                                }}
                                disabled={changingStatus}
                                onClick={() => handleMoveTo(col.key)}
                            >
                                {col.label}
                            </button>
                        ))}
                    </div>
                )}
                {changingStatus && <p className="rk-detail-busy">Měním stav…</p>}
                <div className="rk-detail-delete-row">
                    <button
                        type="button"
                        className="btn-delete"
                        onClick={() => onDelete(item.id)}
                    >
                        Smazat reklamaci
                    </button>
                    <span className="rk-detail-hint">skryje záznam ze seznamu</span>
                </div>
            </div>

            <div className="rk-detail-section">
                <h3>Údaje</h3>
                {saveError && <p className="rk-detail-error">{saveError}</p>}
                <div className="rk-detail-grid">
                    <div className="rk-detail-item rk-detail-item--readonly">
                        <span className="label">Značka:</span>
                        <span className="value">{item.nase_znacka || '—'}</span>
                    </div>
                    {field('Prodejna', 'prodejna')}
                    {field('Název zboží', 'nazev_zbozi')}
                    {field('Dodavatel', 'dodavatel')}
                    {field('Faktura', 'faktura')}
                    {field('EAN', 'ean')}
                    {field('P kód', 'p_kod')}
                    {field('Datum odeslání', 'datum_odeslani', { type: 'date' })}
                    {field('Číslo zásilky', 'cislo_zasilky')}
                    {field('Jejich označení', 'jejich_oznaceni')}
                    {field('Vyskladněno', 'sklad_vyskladneno', { type: 'checkbox' })}
                    {field('Naskladněno', 'sklad_naskladneno', { type: 'checkbox' })}
                    {(currentStatus === REKLAMACE_STATUS.VRIZENE
                        || fields.zpusob_vyrizeni
                        || fields.datum_vyrizeni) && (
                        <>
                            {field('Způsob vyřízení', 'zpusob_vyrizeni', {
                                type: 'select',
                                options: ZPUSOB_VYRIzeni_OPTIONS,
                            })}
                            {field('Datum vyřízení', 'datum_vyrizeni', { type: 'date' })}
                        </>
                    )}
                </div>

                <div className="rk-detail-note">
                    <strong>Poznámka</strong>
                    <textarea
                        className="rk-detail-input"
                        rows={3}
                        value={fields.poznamka}
                        onChange={(e) => setField('poznamka', e.target.value)}
                        placeholder="Poznámka…"
                    />
                </div>
            </div>

            <div className="rk-detail-section">
                <h3>Aktuální stav</h3>
                <div className="rk-current-status">
                    <div
                        className="rk-status-badge"
                        style={{
                            backgroundColor: currentStatusCfg?.color,
                            color: currentStatusCfg?.textColor || '#000',
                        }}
                    >
                        {statusDisplay}
                    </div>
                    <div className="rk-status-info">
                        <div>Vytvořeno: {formatDateTime(item.created_at)}</div>
                        {item.odeslano_dodavateli_at && (
                            <div>Odesláno: {formatDateTime(item.odeslano_dodavateli_at)}</div>
                        )}
                        {item.is_overdue && <div className="rk-overdue">Po termínu – odeslat dodavateli</div>}
                    </div>
                </div>
            </div>
        </Modal>
    );
};

export default ReklamaceDetail;
