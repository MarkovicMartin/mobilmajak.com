import React, { useState, useEffect } from 'react';
import api from '../../services/api';
import './OrderDetail.css';

const OrderDetail = ({ order, onClose, onDelete, onStatusChange }) => {
    const [history, setHistory] = useState([]);
    const [loadingHistory, setLoadingHistory] = useState(true);
    const [newStatus, setNewStatus] = useState(order.status);
    const [statusNote, setStatusNote] = useState('');
    const [changingStatus, setChangingStatus] = useState(false);

    // Definice stavů
    const statusOptions = [
        { value: 'nove', label: 'Nové', icon: '🆕', color: '#ffeb3b' },
        { value: 'objednano', label: 'Objednáno', icon: '📋', color: '#2196f3' },
        { value: 'v_kosiku', label: 'V košíku', icon: '🛒', color: '#ff9800' },
        { value: 'predobjednano', label: 'Předobjednáno', icon: '⏳', color: '#9c27b0' },
        { value: 'neni_skladem', label: 'Není skladem', icon: '❌', color: '#f44336' },
        { value: 'storno', label: 'Storno', icon: '🚫', color: '#757575' },
        { value: 'dorazilo_ceka', label: 'Dorazilo čeká na zákazníka', icon: '📦', color: '#4caf50' },
        { value: 'hotovo', label: 'Hotovo', icon: '✅', color: '#8bc34a' }
    ];

    // Načtení historie objednávky
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

    // Změna stavu
    const handleStatusChange = async () => {
        if (newStatus === order.status) {
            return;
        }

        setChangingStatus(true);
        try {
            const result = await onStatusChange(order.id, newStatus, statusNote);
            if (result.success) {
                // Obnovíme historii
                const response = await api.get(`/orders/orders/${order.id}/history/`);
                setHistory(response.data);
                setStatusNote('');
                // Aktualizujeme aktuální stav v order objektu
                order.status = newStatus;
                order.status_display = statusOptions.find(s => s.value === newStatus)?.label || newStatus;
            } else {
                alert(result.error);
                setNewStatus(order.status); // Vrátíme zpět původní stav
            }
        } catch (err) {
            console.error('Chyba při změně stavu:', err);
            alert('Nepodařilo se změnit stav');
            setNewStatus(order.status);
        } finally {
            setChangingStatus(false);
        }
    };

    // Formátování data a času
    const formatDateTime = (dateString) => {
        const date = new Date(dateString);
        return date.toLocaleString('cs-CZ');
    };

    // Získání aktuálního stavu
    const currentStatusConfig = statusOptions.find(s => s.value === order.status);

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="order-detail-modal" onClick={(e) => e.stopPropagation()}>
                <div className="modal-header">
                    <h2>📦 Detail objednávky #{order.id}</h2>
                    <button className="close-btn" onClick={onClose}>✕</button>
                </div>

                <div className="order-detail-content">
                    {/* Základní informace */}
                    <div className="detail-section">
                        <h3>ℹ️ Základní informace</h3>
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
                                <span className="label">Telefon/Zařízení:</span>
                                <span className="value">{order.typ_telefonu}</span>
                            </div>
                            <div className="detail-item">
                                <span className="label">Díl:</span>
                                <span className="value">
                                    {order.dil}
                                    {order.barva && ` (${order.barva})`}
                                </span>
                            </div>
                            {order.cena && (
                                <div className="detail-item">
                                    <span className="label">Cena:</span>
                                    <span className="value">
                                        {parseFloat(order.cena).toLocaleString('cs-CZ')} Kč
                                    </span>
                                </div>
                            )}
                            {order.servisni_cislo && (
                                <div className="detail-item">
                                    <span className="label">Servisní číslo:</span>
                                    <span className="value">{order.servisni_cislo}</span>
                                </div>
                            )}
                            {order.dodavatel && (
                                <div className="detail-item">
                                    <span className="label">Dodavatel:</span>
                                    <span className="value">{order.dodavatel}</span>
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

                    {/* Aktuální stav */}
                    <div className="detail-section">
                        <h3>📊 Aktuální stav</h3>
                        <div className="current-status">
                            <div 
                                className="status-badge"
                                style={{ backgroundColor: currentStatusConfig?.color }}
                            >
                                <span className="status-icon">{currentStatusConfig?.icon}</span>
                                <span className="status-text">{order.status_display}</span>
                            </div>
                            <div className="status-info">
                                <div>Vytvořeno: {formatDateTime(order.datum_vytvoreni)}</div>
                                <div>Založil: {order.zalozil?.jmeno}</div>
                                <div>Poslední změna: {order.posledni_zmena_uzivatel?.jmeno}</div>
                                {order.celkova_doba_procesu_text && (
                                    <div>Celková doba: {order.celkova_doba_procesu_text}</div>
                                )}
                            </div>
                        </div>
                    </div>

                    {/* Změna stavu */}
                    <div className="detail-section">
                        <h3>🔄 Změna stavu</h3>
                        <div className="status-change">
                            <div className="status-change-form">
                                <div className="form-row">
                                    <select
                                        value={newStatus}
                                        onChange={(e) => setNewStatus(e.target.value)}
                                        className="status-select"
                                    >
                                        {statusOptions.map(option => (
                                            <option key={option.value} value={option.value}>
                                                {option.icon} {option.label}
                                            </option>
                                        ))}
                                    </select>
                                    <button
                                        onClick={handleStatusChange}
                                        disabled={changingStatus || newStatus === order.status}
                                        className="btn btn-primary"
                                    >
                                        {changingStatus ? 'Měním...' : 'Změnit stav'}
                                    </button>
                                </div>
                                <textarea
                                    value={statusNote}
                                    onChange={(e) => setStatusNote(e.target.value)}
                                    placeholder="Poznámka ke změně stavu (volitelné)"
                                    className="status-note"
                                    rows="2"
                                />
                            </div>
                        </div>
                    </div>

                    {/* Historie změn */}
                    <div className="detail-section">
                        <h3>📜 Historie změn</h3>
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
                                    {history.map((item, index) => (
                                        <div key={item.id} className="timeline-item">
                                            <div className="timeline-marker">
                                                <span className="timeline-icon">
                                                    {statusOptions.find(s => s.value === item.novy_status)?.icon || '📋'}
                                                </span>
                                            </div>
                                            <div className="timeline-content">
                                                <div className="timeline-header">
                                                    <strong>
                                                        {item.puvodni_status_display ? 
                                                            `${item.puvodni_status_display} → ${item.novy_status_display}` :
                                                            item.novy_status_display
                                                        }
                                                    </strong>
                                                    <span className="timeline-time">
                                                        {formatDateTime(item.datum_zmeny)}
                                                    </span>
                                                </div>
                                                <div className="timeline-user">
                                                    👤 {item.uzivatel?.jmeno}
                                                </div>
                                                {item.poznamka && (
                                                    <div className="timeline-note">
                                                        📝 {item.poznamka}
                                                    </div>
                                                )}
                                                {item.doba_ve_stavu_text && (
                                                    <div className="timeline-duration">
                                                        ⏱️ Doba ve stavu: {item.doba_ve_stavu_text}
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Akce */}
                    <div className="detail-actions">
                        <button 
                            className="btn btn-danger"
                            onClick={() => onDelete(order.id)}
                        >
                            🗑️ Smazat objednávku
                        </button>
                        <button 
                            className="btn btn-secondary"
                            onClick={onClose}
                        >
                            Zavřít
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default OrderDetail; 