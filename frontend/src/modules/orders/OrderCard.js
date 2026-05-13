import React from 'react';
import { useDraggable } from '@dnd-kit/core';
import './OrderCard.css';

const OrderCard = ({ order, isDragging = false, onOrderClick, onDeleteOrder }) => {
    const {
        attributes,
        listeners,
        setNodeRef,
        transform,
        isDragging: isCurrentlyDragging,
    } = useDraggable({
        id: order.id,
    });

    const style = transform ? {
        transform: `translate3d(${transform.x}px, ${transform.y}px, 0)`,
    } : undefined;

    // Formátování data
    const formatDate = (dateString) => {
        const date = new Date(dateString);
        const now = new Date();
        const diffTime = Math.abs(now - date);
        const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
        
        if (diffDays === 1) {
            return 'Dnes';
        } else if (diffDays === 2) {
            return 'Včera';
        } else if (diffDays <= 7) {
            return `${diffDays - 1} dny zpět`;
        } else {
            return date.toLocaleDateString('cs-CZ');
        }
    };

    // Priorita objednávky podle stáří
    const getPriorityClass = () => {
        const created = new Date(order.datum_vytvoreni);
        const now = new Date();
        const diffHours = Math.abs(now - created) / (1000 * 60 * 60);
        
        if (diffHours > 48) return 'priority-high';
        if (diffHours > 24) return 'priority-medium';
        return 'priority-normal';
    };

    return (
        <div
            ref={setNodeRef}
            style={style}
            className={`order-card ${isDragging || isCurrentlyDragging ? 'dragging' : ''} ${getPriorityClass()}`}
            {...listeners}
            {...attributes}
        >
            {/* Header karty */}
            <div className="card-header">
                <div className="card-id">
                    #{order.id}
                </div>
                <div className="card-actions">
                    <button
                        className="card-action-btn info"
                        onClick={(e) => {
                            e.stopPropagation();
                            onOrderClick(order);
                        }}
                        title="Detail objednávky"
                    >
                        ℹ️
                    </button>
                    <button
                        className="card-action-btn delete"
                        onClick={(e) => {
                            e.stopPropagation();
                            onDeleteOrder(order.id);
                        }}
                        title="Smazat objednávku"
                    >
                        🗑️
                    </button>
                </div>
            </div>

            {/* Informace o zákazníkovi */}
            <div className="card-customer">
                <div className="customer-name">
                    👤 {order.jmeno_zakaznika} {order.prijmeni_zakaznika}
                </div>
                <div className="customer-phone">
                    📞 {order.telefon_zakaznika}
                </div>
            </div>

            {/* Informace o dílu */}
            <div className="card-item">
                <div className="item-device">
                    📱 {order.typ_telefonu}
                </div>
                <div className="item-part">
                    🔧 {order.dil}
                    {order.barva && (
                        <span className="item-color"> ({order.barva})</span>
                    )}
                </div>
            </div>

            {/* Metadata */}
            <div className="card-metadata">
                <div className="metadata-row">
                    <span className="metadata-label">📅 Vytvořeno:</span>
                    <span className="metadata-value">{formatDate(order.datum_vytvoreni)}</span>
                </div>
                <div className="metadata-row">
                    <span className="metadata-label">👨‍💼 Založil:</span>
                    <span className="metadata-value">{order.zalozil?.jmeno || 'Neznámý'}</span>
                </div>
                {order.doba_od_vytvoreni && (
                    <div className="metadata-row">
                        <span className="metadata-label">⏰ Doba:</span>
                        <span className="metadata-value">{order.doba_od_vytvoreni}</span>
                    </div>
                )}
            </div>

            {/* Cena pokud je zadána */}
            {order.cena && (
                <div className="card-price">
                    💰 {parseFloat(order.cena).toLocaleString('cs-CZ')} Kč
                </div>
            )}

            {/* Poznámka pokud je zadána */}
            {order.poznamka && (
                <div className="card-note">
                    📝 {order.poznamka.length > 50 
                        ? `${order.poznamka.substring(0, 50)}...` 
                        : order.poznamka
                    }
                </div>
            )}

            {/* Servisní číslo pokud je zadáno */}
            {order.servisni_cislo && (
                <div className="card-service-number">
                    🔢 {order.servisni_cislo}
                </div>
            )}

            {/* Drag handle indikátor */}
            <div className="drag-handle">
                <span className="drag-icon">⋮⋮</span>
            </div>
        </div>
    );
};

export default OrderCard; 