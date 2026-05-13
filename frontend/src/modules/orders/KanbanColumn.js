import React from 'react';
import { useDroppable } from '@dnd-kit/core';
import OrderCard from './OrderCard';
import './KanbanColumn.css';

const KanbanColumn = ({ 
    id, 
    title, 
    icon, 
    color, 
    textColor,
    orders, 
    count, 
    isDropTarget,
    onOrderClick,
    onDeleteOrder 
}) => {
    const { setNodeRef, isOver } = useDroppable({
        id: `column-${id}`,
    });

    return (
        <div 
            ref={setNodeRef}
            className={`kanban-column ${isOver || isDropTarget ? 'drag-over' : ''}`}
        >
            {/* Header sloupce */}
            <div 
                className="column-header"
                style={{ 
                    backgroundColor: color,
                    color: textColor
                }}
            >
                <div className="header-content">
                    <span className="column-icon">{icon}</span>
                    <span className="column-title">{title}</span>
                    <span className="column-count">({count})</span>
                </div>
            </div>

            {/* Seznam objednávek */}
            <div className="column-content">
                {orders.length === 0 ? (
                    <div className="empty-column">
                        <div className="empty-message">
                            <span className="empty-icon">📋</span>
                            <p>Žádné objednávky</p>
                        </div>
                    </div>
                ) : (
                    <div className="orders-list">
                        {orders.map(order => (
                            <OrderCard
                                key={order.id}
                                order={order}
                                onOrderClick={onOrderClick}
                                onDeleteOrder={onDeleteOrder}
                            />
                        ))}
                    </div>
                )}
            </div>

            {/* Drop zone indikátor */}
            {(isOver || isDropTarget) && (
                <div className="drop-zone-indicator">
                    <div className="drop-zone-content">
                        <span className="drop-icon">📥</span>
                        <p>Přetáhněte sem objednávku</p>
                    </div>
                </div>
            )}
        </div>
    );
};

export default KanbanColumn; 