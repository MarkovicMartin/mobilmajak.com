import React, { useState, useEffect } from 'react';
import Modal from '../../components/Modal';
import api from '../../services/api';
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

const OrderDetail = ({ order, onClose, onDelete, onStatusChange }) => {
    const [history, setHistory] = useState([]);
    const [loadingHistory, setLoadingHistory] = useState(true);
    const [currentStatus, setCurrentStatus] = useState(order.status);
    const [statusDisplay, setStatusDisplay] = useState(
        order.status_display || statusLabel(order.status)
    );
    const [dodavatel, setDodavatel] = useState(order.dodavatel || '');
    const [statusNote, setStatusNote] = useState('');
    const [changingStatus, setChangingStatus] = useState(false);

    useEffect(() => {
        setCurrentStatus(order.status);
        setStatusDisplay(order.status_display || statusLabel(order.status));
        setDodavatel(order.dodavatel || '');
    }, [order.id, order.status, order.status_display, order.dodavatel]);

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
    const repairLink = myrepairUrl(order.servisni_cislo);

    const handleMoveTo = async (newStatus) => {
        if (newStatus === currentStatus || changingStatus) return;

        let nextDodavatel = null;
        if (STATUSES_REQUIRING_DODAVATEL.has(newStatus) && !(dodavatel || '').trim()) {
            const entered = window.prompt('Zadejte dodavatele (povinné pro tento stav):');
            if (!entered || !entered.trim()) {
                alert('Dodavatel je povinný při přesunu do v košíku / objednáno.');
                return;
            }
            nextDodavatel = entered.trim();
        }

        setChangingStatus(true);
        try {
            const result = await onStatusChange(order.id, newStatus, statusNote, nextDodavatel);
            if (result.success) {
                const response = await api.get(`/orders/orders/${order.id}/history/`);
                setHistory(response.data);
                setStatusNote('');
                setCurrentStatus(newStatus);
                setStatusDisplay(statusLabel(newStatus));
                if (nextDodavatel) {
                    setDodavatel(nextDodavatel);
                }
            } else {
                const err = result.error;
                const msg = typeof err === 'object'
                    ? (err.dodavatel?.[0] || err.error || JSON.stringify(err))
                    : err;
                alert(msg);
            }
        } catch (err) {
            console.error('Chyba při změně stavu:', err);
            alert('Nepodařilo se změnit stav');
        } finally {
            setChangingStatus(false);
        }
    };

    const formatDateTime = (dateString) => {
        const date = new Date(dateString);
        return date.toLocaleString('cs-CZ');
    };

    return (
        <Modal
            title={`Detail objednávky #${order.id}`}
            onClose={onClose}
            size="md"
            bodyClassName="order-detail-content"
            footer={(
                <>
                    <button type="button" className="btn-delete" onClick={() => onDelete(order.id)}>
                        Smazat objednávku
                    </button>
                    <button type="button" className="btn-cancel" onClick={onClose}>
                        Zavřít
                    </button>
                </>
            )}
        >
            <div className="detail-section">
                <h3>Základní informace</h3>
                <div className="detail-grid">
                    <div className="detail-item">
                        <span className="label">Zákazník:</span>
                        <span className="value">
                            {order.jmeno_zakaznika} {order.prijmeni_zakaznika}
                        </span>
                    </div>
                    <div className="detail-item">
                        <span className="label">Telefon:</span>
                        <span className="value">{order.telefon_zakaznika}</span>
                    </div>
                    <div className="detail-item">
                        <span className="label">Typ:</span>
                        <span className="value">{order.typ_telefonu}</span>
                    </div>
                    <div className="detail-item">
                        <span className="label">Díl:</span>
                        <span className="value">
                            {order.dil}
                            {order.barva && ` (${order.barva})`}
                        </span>
                    </div>
                    {order.cena != null && order.cena !== '' && (
                        <div className="detail-item">
                            <span className="label">Cena:</span>
                            <span className="value">
                                {parseFloat(order.cena).toLocaleString('cs-CZ')} Kč
                            </span>
                        </div>
                    )}
                    {order.servisni_cislo && (
                        <div className="detail-item">
                            <span className="label">Serviska:</span>
                            <span className="value">
                                {repairLink ? (
                                    <a
                                        href={repairLink}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                    >
                                        {order.servisni_cislo}
                                    </a>
                                ) : (
                                    order.servisni_cislo
                                )}
                            </span>
                        </div>
                    )}
                    <div className="detail-item">
                        <span className="label">Prodejna:</span>
                        <span className="value">{formatProdejna(order.prodejna)}</span>
                    </div>
                    <div className="detail-item">
                        <span className="label">Zadal:</span>
                        <span className="value">{formatZadal(order.zalozil)}</span>
                    </div>
                    {(order.symplio_objednavka_id || order.symplio_url) && (
                        <div className="detail-item">
                            <span className="label">Symplio:</span>
                            <span className="value">
                                {order.symplio_url ? (
                                    <a
                                        href={order.symplio_url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                    >
                                        Objednávka {order.symplio_objednavka_id}
                                    </a>
                                ) : (
                                    order.symplio_objednavka_id
                                )}
                            </span>
                        </div>
                    )}
                    {dodavatel && (
                        <div className="detail-item">
                            <span className="label">Dodavatel:</span>
                            <span className="value">{dodavatel}</span>
                        </div>
                    )}
                </div>

                {order.poznamka && (
                    <div className="detail-note">
                        <strong>Poznámka:</strong>
                        <p>{order.poznamka}</p>
                    </div>
                )}
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

                    {moveTargets.secondary.length > 0 && (
                        <div className="status-move__secondary">
                            <span className="status-move__secondary-label">Další:</span>
                            <div className="status-move__buttons" role="group" aria-label="Další stavy">
                                {moveTargets.secondary.map((opt) => (
                                    <button
                                        key={opt.value}
                                        type="button"
                                        className="status-move__btn status-move__btn--secondary"
                                        style={{
                                            backgroundColor: opt.color,
                                            color: opt.textColor,
                                        }}
                                        disabled={changingStatus}
                                        onClick={() => handleMoveTo(opt.value)}
                                    >
                                        {opt.label}
                                    </button>
                                ))}
                            </div>
                        </div>
                    )}

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
