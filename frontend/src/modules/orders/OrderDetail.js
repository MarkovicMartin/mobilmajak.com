import React, { useState, useEffect, useMemo, useRef } from 'react';
import Modal from '../../components/Modal';
import api from '../../services/api';
import { copyToClipboard } from '../../utils/clipboard';
import {
    ALL_STATUS_OPTIONS,
    STATUSES_REQUIRING_DODAVATEL,
    getMoveTargets,
    statusLabel,
    myrepairUrl,
    formatZadal,
    formatProdejna,
} from './orderHelpers';
import './OrderDetail.css';

const emptyFieldsFromOrder = (order) => ({
    jmeno_zakaznika: order.jmeno_zakaznika || '',
    prijmeni_zakaznika: order.prijmeni_zakaznika || '',
    telefon_zakaznika: order.telefon_zakaznika || '',
    typ_telefonu: order.typ_telefonu || '',
    dil: order.dil || '',
    barva: order.barva || '',
    cena: order.cena != null && order.cena !== '' ? String(order.cena) : '',
    dodavatel: order.dodavatel || '',
    servisni_cislo: order.servisni_cislo || '',
    poznamka: order.poznamka || '',
});

const OrderDetail = ({ order, onClose, onDelete, onStatusChange, onUpdate }) => {
    const [history, setHistory] = useState([]);
    const [loadingHistory, setLoadingHistory] = useState(true);
    const [currentStatus, setCurrentStatus] = useState(order.status);
    const [statusDisplay, setStatusDisplay] = useState(
        order.status_display || statusLabel(order.status)
    );
    const [fields, setFields] = useState(() => emptyFieldsFromOrder(order));
    const [baseline, setBaseline] = useState(() => emptyFieldsFromOrder(order));
    const [statusNote, setStatusNote] = useState('');
    const [changingStatus, setChangingStatus] = useState(false);
    const [saving, setSaving] = useState(false);
    const [saveError, setSaveError] = useState('');
    const [phoneCopied, setPhoneCopied] = useState(false);
    const mountedRef = useRef(true);

    useEffect(() => {
        return () => {
            mountedRef.current = false;
        };
    }, []);

    useEffect(() => {
        setCurrentStatus(order.status);
        setStatusDisplay(order.status_display || statusLabel(order.status));
        const next = emptyFieldsFromOrder(order);
        setFields(next);
        setBaseline(next);
        setSaveError('');
    }, [order]);

    useEffect(() => {
        const loadHistory = async () => {
            try {
                setLoadingHistory(true);
                const response = await api.get(`/orders/orders/${order.id}/history/`);
                setHistory(response.data);
            } catch (err) {
                console.error('Chyba při načítání historie:', err);
            } finally {
                setLoadingHistory(false);
            }
        };

        loadHistory();
    }, [order.id]);

    const moveTargets = getMoveTargets(currentStatus);
    const currentStatusConfig = ALL_STATUS_OPTIONS.find((s) => s.value === currentStatus);
    const repairLink = myrepairUrl(fields.servisni_cislo);
    const phoneValue = (fields.telefon_zakaznika || '').trim();
    const detailTitle = [fields.typ_telefonu, fields.dil].filter(Boolean).join(' · ') || 'Objednávka';

    const dirty = useMemo(() => {
        return Object.keys(baseline).some((key) => String(fields[key] ?? '') !== String(baseline[key] ?? ''));
    }, [fields, baseline]);

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
                if (String(fields[key] ?? '') !== String(baseline[key] ?? '')) {
                    if (key === 'cena') {
                        const raw = String(fields[key] ?? '').trim();
                        patch[key] = raw === '' ? null : raw;
                    } else {
                        patch[key] = fields[key];
                    }
                }
            });
            const result = await onUpdate(order.id, patch);
            if (result.success === false) {
                const err = result.error;
                const msg = typeof err === 'object'
                    ? (Object.values(err).flat?.()?.[0] || err.detail || JSON.stringify(err))
                    : (err || 'Uložení selhalo');
                setSaveError(typeof msg === 'string' ? msg : 'Uložení selhalo');
                return;
            }
            // Po úspěšném uložení má edit okno zmizet (zabránění “záseku”).
            if (onClose) {
                onClose();
                return;
            }

            if (result.data) {
                const next = emptyFieldsFromOrder(result.data);
                setFields(next);
                setBaseline(next);
            } else {
                setBaseline({ ...fields });
            }
        } catch (err) {
            if (mountedRef.current) setSaveError('Uložení selhalo');
        } finally {
            if (mountedRef.current) setSaving(false);
        }
    };

    const handleMoveTo = async (newStatus) => {
        if (newStatus === currentStatus || changingStatus) return;

        let nextDodavatel = null;
        if (STATUSES_REQUIRING_DODAVATEL.has(newStatus) && !(fields.dodavatel || '').trim()) {
            const entered = window.prompt('Zadejte dodavatele (povinné pro tento stav):');
            if (!entered || !entered.trim()) {
                alert('Dodavatel je povinný při přesunu do v košíku / objednáno.');
                return;
            }
            nextDodavatel = entered.trim();
        }

        const prevStatus = currentStatus;
        const prevDisplay = statusDisplay;
        const prevDodavatel = fields.dodavatel;

        setChangingStatus(true);
        setCurrentStatus(newStatus);
        setStatusDisplay(statusLabel(newStatus));
        if (nextDodavatel) {
            setFields((prev) => ({ ...prev, dodavatel: nextDodavatel }));
            setBaseline((prev) => ({ ...prev, dodavatel: nextDodavatel }));
        }
        const noteForApi = statusNote;
        setStatusNote('');

        try {
            const result = await onStatusChange(order.id, newStatus, noteForApi, nextDodavatel);
            if (result.success) {
                api.get(`/orders/orders/${order.id}/history/`)
                    .then((response) => setHistory(response.data))
                    .catch(() => {});
            } else {
                setCurrentStatus(prevStatus);
                setStatusDisplay(prevDisplay);
                setStatusNote(noteForApi);
                if (nextDodavatel) {
                    setFields((prev) => ({ ...prev, dodavatel: prevDodavatel }));
                    setBaseline((prev) => ({ ...prev, dodavatel: prevDodavatel }));
                }
                const err = result.error;
                const msg = typeof err === 'object'
                    ? (err.dodavatel?.[0] || err.error || JSON.stringify(err))
                    : (typeof err === 'string' ? err : 'Nepodařilo se změnit stav');
                alert(typeof msg === 'string' && !msg.trim().startsWith('<')
                    ? msg
                    : 'Nepodařilo se změnit stav');
            }
        } catch (err) {
            console.error('Chyba při změně stavu:', err);
            setCurrentStatus(prevStatus);
            setStatusDisplay(prevDisplay);
            setStatusNote(noteForApi);
            if (nextDodavatel) {
                setFields((prev) => ({ ...prev, dodavatel: prevDodavatel }));
                setBaseline((prev) => ({ ...prev, dodavatel: prevDodavatel }));
            }
            alert('Nepodařilo se změnit stav');
        } finally {
            setChangingStatus(false);
        }
    };

    const formatDateTime = (dateString) => {
        const date = new Date(dateString);
        return date.toLocaleString('cs-CZ');
    };

    const field = (label, name, opts = {}) => (
        <label className={`detail-item detail-item--field${opts.wide ? ' detail-item--nolabel' : ''}`}>
            {label ? <span className="label">{label}</span> : null}
            {opts.multiline ? (
                <textarea
                    className="detail-edit__input"
                    rows={3}
                    value={fields[name]}
                    onChange={(e) => setField(name, e.target.value)}
                    placeholder={opts.placeholder || ''}
                />
            ) : (
                <input
                    className="detail-edit__input"
                    type={opts.type || 'text'}
                    step={opts.type === 'number' ? '0.01' : undefined}
                    value={fields[name]}
                    onChange={(e) => setField(name, e.target.value)}
                    placeholder={opts.placeholder || ''}
                />
            )}
            {name === 'servisni_cislo' && repairLink ? (
                <a
                    className="detail-myrepair-btn"
                    href={repairLink}
                    target="_blank"
                    rel="noopener noreferrer"
                    title="Otevřít v MyRepair"
                    onClick={(e) => e.stopPropagation()}
                >
                    MyRepair ↗
                </a>
            ) : null}
            {name === 'telefon_zakaznika' && phoneValue && (
                <button
                    type="button"
                    className="detail-field-link detail-field-link--btn"
                    title={phoneCopied ? 'Zkopírováno' : 'Zkopírovat telefon'}
                    onClick={async () => {
                        const result = await copyToClipboard(phoneValue);
                        if (result.success) {
                            setPhoneCopied(true);
                            window.setTimeout(() => setPhoneCopied(false), 1200);
                        }
                    }}
                >
                    {phoneCopied ? 'Zkopírováno' : 'Kopírovat'}
                </button>
            )}
        </label>
    );

    return (
        <Modal
            title={detailTitle}
            onClose={onClose}
            size="md"
            bodyClassName="order-detail-content"
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
            <div className="detail-section detail-section--move">
                <h3>Přesunout do</h3>
                <div className="status-move">
                    <div className="status-move__buttons" role="group" aria-label="Hlavní stavy">
                        {moveTargets.main.map((col) => (
                            <button
                                key={col.key}
                                type="button"
                                className="status-move__btn"
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

                    <textarea
                        value={statusNote}
                        onChange={(e) => setStatusNote(e.target.value)}
                        placeholder="Poznámka ke změně stavu (volitelné)"
                        className="status-note"
                        rows="2"
                        disabled={changingStatus}
                    />
                    {changingStatus && (
                        <p className="status-move__busy">Měním stav…</p>
                    )}
                </div>
                <div className="detail-delete-row">
                    <button
                        type="button"
                        className="btn-delete detail-delete-btn"
                        onClick={() => onDelete(order.id)}
                    >
                        Smazat objednávku
                    </button>
                    <span className="detail-delete-hint">např. když zákazník zrušil</span>
                </div>
            </div>

            <div className="detail-section">
                <h3>Údaje</h3>
                {saveError && <p className="detail-save-error">{saveError}</p>}
                <div className="detail-grid">
                    {field('Model', 'typ_telefonu')}
                    {field('Díl', 'dil')}
                    {field('Barva', 'barva')}
                    {field('Serviska', 'servisni_cislo')}
                    {field('Cena', 'cena', { type: 'number' })}
                    {field('Dodavatel', 'dodavatel')}
                    <div className="detail-item detail-item--readonly">
                        <span className="label">Prodejna:</span>
                        <span className="value">{formatProdejna(order.prodejna)}</span>
                    </div>
                    <div className="detail-item detail-item--readonly">
                        <span className="label">Zadal:</span>
                        <span className="value">{formatZadal(order.zalozil)}</span>
                    </div>
                </div>

                <div className="detail-grid detail-grid--customer">
                    {field('Jméno', 'jmeno_zakaznika')}
                    {field('Příjmení', 'prijmeni_zakaznika')}
                    {field('Telefon', 'telefon_zakaznika')}
                </div>

                <div className="detail-note detail-note--editable">
                    <strong>Poznámka</strong>
                    <textarea
                        className="detail-edit__input"
                        rows={3}
                        value={fields.poznamka}
                        onChange={(e) => setField('poznamka', e.target.value)}
                        placeholder="Poznámka…"
                    />
                </div>
            </div>

            <div className="detail-section">
                <h3>Aktuální stav</h3>
                <div className="current-status">
                    <div
                        className="status-badge"
                        style={{
                            backgroundColor: currentStatusConfig?.color,
                            color: currentStatusConfig?.textColor || '#fff',
                        }}
                    >
                        <span className="status-text">{statusDisplay}</span>
                    </div>
                    <div className="status-info">
                        <div>Vytvořeno: {formatDateTime(order.datum_vytvoreni)}</div>
                        <div>Založil: {formatZadal(order.zalozil)}</div>
                        <div>Poslední změna: {formatZadal(order.posledni_zmena_uzivatel)}</div>
                        {order.celkova_doba_procesu_text && (
                            <div>Celková doba: {order.celkova_doba_procesu_text}</div>
                        )}
                    </div>
                </div>
            </div>

            <div className="detail-section">
                <h3>Historie změn</h3>
                <div className="history-section">
                    {loadingHistory ? (
                        <div className="loading">
                            <div className="spinner"></div>
                            <p>Načítám historii...</p>
                        </div>
                    ) : history.length === 0 ? (
                        <p className="no-history">Žádná historie změn</p>
                    ) : (
                        <div className="history-timeline">
                            {history.map((item) => (
                                <div key={item.id} className="timeline-item">
                                    <div className="timeline-marker">
                                        <span className="timeline-icon">•</span>
                                    </div>
                                    <div className="timeline-content">
                                        <div className="timeline-header">
                                            <strong>
                                                {item.puvodni_status_display
                                                    ? `${item.puvodni_status_display} → ${item.novy_status_display}`
                                                    : item.novy_status_display}
                                            </strong>
                                            <span className="timeline-time">
                                                {formatDateTime(item.datum_zmeny)}
                                            </span>
                                        </div>
                                        <div className="timeline-user">
                                            {formatZadal(item.uzivatel)}
                                        </div>
                                        {item.poznamka && (
                                            <div className="timeline-note">{item.poznamka}</div>
                                        )}
                                        {item.doba_ve_stavu_text && (
                                            <div className="timeline-duration">
                                                Doba ve stavu: {item.doba_ve_stavu_text}
                                            </div>
                                        )}
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </Modal>
    );
};

export default OrderDetail;
