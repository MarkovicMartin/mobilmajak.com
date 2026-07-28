import React from 'react';
import { useDroppable } from '@dnd-kit/core';
import OrderRow from './OrderRow';
import './KanbanColumn.css';
import './OrderRow.css';

const ROW_HEADERS = [
    'Datum', 'Model', 'Věc', 'Barva', 'Serviska', 'Zákazník',
    'Telefon', 'Cena', 'Zadal', 'Prodejna', 'Dodavatel', '',
];

const KanbanColumn = ({
    id,
    title,
    color,
    textColor,
    orders,
    count,
    isDropTarget,
    onOrderClick,
    onDeleteOrder,
}) => {
    const { setNodeRef, isOver } = useDroppable({
        id: `column-${id}`,
    });

    return (
        <div
            ref={setNodeRef}
            className={`kanban-column kanban-column--dense ${isOver || isDropTarget ? 'drag-over' : ''}`}
        >
            <div
                className="column-header"
                style={{
                    backgroundColor: color,
                    color: textColor,
                }}
            >
                <div className="header-content">
                    <span className="column-title">{title}</span>
                    <span className="column-count">({count})</span>
                </div>
            </div>

            <div className="column-content column-content--dense">
                <div className="order-row-header" aria-hidden="true">
                    {ROW_HEADERS.map((label, i) => (
                        <span key={`${label}-${i}`}>{label}</span>
                    ))}
                </div>

                {orders.length === 0 ? (
                    <div className="empty-column empty-column--dense">
                        <p>Žádné objednávky</p>
                    </div>
                ) : (
                    <div className="orders-list orders-list--dense">
                        {orders.map((order) => (
                            <OrderRow
                                key={order.id}
                                order={order}
                                onOrderClick={onOrderClick}
                                onDeleteOrder={onDeleteOrder}
                            />
                        ))}
                    </div>
                )}
            </div>

            {(isOver || isDropTarget) && (
                <div className="drop-zone-indicator" aria-hidden="true" />
            )}
        </div>
    );
};

export default KanbanColumn;
