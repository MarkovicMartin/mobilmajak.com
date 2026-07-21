import React, { useState } from 'react';
import {
    DndContext,
    DragOverlay,
    useSensor,
    useSensors,
    PointerSensor,
    KeyboardSensor,
    TouchSensor,
} from '@dnd-kit/core';
import { sortableKeyboardCoordinates } from '@dnd-kit/sortable';
import OrderRow from './OrderRow';
import KanbanColumn from './KanbanColumn';
import {
    MAIN_STATUS_COLUMNS,
    MAIN_STATUS_KEYS,
    STATUSES_REQUIRING_DODAVATEL,
    ALL_STATUS_OPTIONS,
} from './orderHelpers';
import './KanbanBoard.css';

const KanbanBoard = ({
    kanbanData,
    onStatusChange,
    onOrderClick,
    onDeleteOrder,
    loading,
    statusFilter = '',
}) => {
    const [activeOrder, setActiveOrder] = useState(null);
    const [dragOverColumn, setDragOverColumn] = useState(null);

    const sensors = useSensors(
        useSensor(PointerSensor, {
            activationConstraint: { distance: 8 },
        }),
        useSensor(TouchSensor, {
            activationConstraint: { delay: 250, tolerance: 8 },
        }),
        useSensor(KeyboardSensor, {
            coordinateGetter: sortableKeyboardCoordinates,
        })
    );

    const visibleColumns = (() => {
        // Legacy predobjednano is folded into objednano on the API
        const effectiveFilter = statusFilter === 'predobjednano' ? 'objednano' : statusFilter;

        if (effectiveFilter && !MAIN_STATUS_KEYS.includes(effectiveFilter)) {
            const opt = ALL_STATUS_OPTIONS.find((s) => s.value === effectiveFilter);
            return [{
                key: effectiveFilter,
                label: opt?.label || effectiveFilter,
                color: opt?.color || '#757575',
                textColor: '#fff',
            }];
        }
        if (effectiveFilter && MAIN_STATUS_KEYS.includes(effectiveFilter)) {
            return MAIN_STATUS_COLUMNS.filter((c) => c.key === effectiveFilter);
        }
        return MAIN_STATUS_COLUMNS;
    })();

    const handleDragStart = (event) => {
        const orderId = event.active.id;
        let foundOrder = null;
        if (kanbanData) {
            Object.values(kanbanData).forEach((column) => {
                if (column?.orders) {
                    const order = column.orders.find((o) => o.id === orderId);
                    if (order) foundOrder = order;
                }
            });
        }
        setActiveOrder(foundOrder);
    };

    const handleDragOver = (event) => {
        const { over } = event;
        if (over?.id?.startsWith?.('column-')) {
            setDragOverColumn(over.id.replace('column-', ''));
        } else {
            setDragOverColumn(null);
        }
    };

    const handleDragEnd = async (event) => {
        const { active, over } = event;
        setActiveOrder(null);
        setDragOverColumn(null);
        if (!over) return;

        const orderId = active.id;
        let newStatus = null;

        if (String(over.id).startsWith('column-')) {
            newStatus = String(over.id).replace('column-', '');
        } else if (kanbanData) {
            Object.keys(kanbanData).forEach((status) => {
                const orders = kanbanData[status]?.orders;
                if (orders?.find((o) => o.id === over.id)) {
                    newStatus = status;
                }
            });
        }

        if (!newStatus || !activeOrder || activeOrder.status === newStatus) {
            return;
        }

        // Drag only onto main board targets (or the filtered extra column)
        const allowed = new Set(visibleColumns.map((c) => c.key));
        if (!allowed.has(newStatus)) {
            return;
        }

        let dodavatel = null;
        if (STATUSES_REQUIRING_DODAVATEL.has(newStatus) && !(activeOrder.dodavatel || '').trim()) {
            const entered = window.prompt('Zadejte dodavatele (povinné pro tento stav):');
            if (!entered || !entered.trim()) {
                alert('Dodavatel je povinný při přesunu do v košíku / objednáno.');
                return;
            }
            dodavatel = entered.trim();
        }

        const result = await onStatusChange(orderId, newStatus, '', dodavatel);
        if (!result.success) {
            const err = result.error;
            const msg = typeof err === 'object'
                ? (err.dodavatel?.[0] || err.error || JSON.stringify(err))
                : err;
            alert(msg);
        }
    };

    if (loading && (!kanbanData || Object.keys(kanbanData).length === 0)) {
        return (
            <div className="kanban-board">
                <div className="loading-board">
                    <div className="spinner"></div>
                    <p>Načítám objednávky...</p>
                </div>
            </div>
        );
    }

    return (
        <DndContext
            sensors={sensors}
            onDragStart={handleDragStart}
            onDragOver={handleDragOver}
            onDragEnd={handleDragEnd}
        >
            <div className="kanban-board kanban-board--dense">
                <div className="kanban-columns kanban-columns--stacked">
                    {visibleColumns.map((config) => {
                        const columnData = (kanbanData && kanbanData[config.key]) || {
                            orders: [],
                            count: 0,
                        };
                        return (
                            <KanbanColumn
                                key={config.key}
                                id={config.key}
                                title={config.label}
                                color={config.color}
                                textColor={config.textColor}
                                orders={columnData.orders || []}
                                count={columnData.count || 0}
                                isDropTarget={dragOverColumn === config.key}
                                onOrderClick={onOrderClick}
                                onDeleteOrder={onDeleteOrder}
                            />
                        );
                    })}
                </div>

                <DragOverlay>
                    {activeOrder ? (
                        <OrderRow
                            order={activeOrder}
                            isDragging
                            onOrderClick={() => {}}
                            onDeleteOrder={() => {}}
                        />
                    ) : null}
                </DragOverlay>
            </div>
        </DndContext>
    );
};

export default KanbanBoard;
