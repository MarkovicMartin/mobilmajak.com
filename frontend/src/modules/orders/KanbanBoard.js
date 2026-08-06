import React, { useState, useEffect } from 'react';
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
    ACTIVE_STATUS_COLUMNS,
    DONE_STATUS_COLUMN,
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
    searchActive = false,
}) => {
    const [activeOrder, setActiveOrder] = useState(null);
    const [dragOverColumn, setDragOverColumn] = useState(null);
    const [doneExpanded, setDoneExpanded] = useState(false);

    useEffect(() => {
        if (searchActive || statusFilter === 'hotovo') {
            setDoneExpanded(true);
        } else {
            setDoneExpanded(false);
        }
    }, [searchActive, statusFilter]);

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

    const { activeColumns, showDoneSeparately } = (() => {
        const effectiveFilter = statusFilter === 'predobjednano' ? 'objednano' : statusFilter;

        if (effectiveFilter && !MAIN_STATUS_KEYS.includes(effectiveFilter)) {
            const opt = ALL_STATUS_OPTIONS.find((s) => s.value === effectiveFilter);
            return {
                activeColumns: [{
                    key: effectiveFilter,
                    label: opt?.label || effectiveFilter,
                    color: opt?.color || '#757575',
                    textColor: '#fff',
                }],
                showDoneSeparately: false,
            };
        }
        if (effectiveFilter === 'hotovo') {
            return {
                activeColumns: [],
                showDoneSeparately: true,
            };
        }
        if (effectiveFilter && MAIN_STATUS_KEYS.includes(effectiveFilter)) {
            return {
                activeColumns: MAIN_STATUS_COLUMNS.filter((c) => c.key === effectiveFilter),
                showDoneSeparately: false,
            };
        }
        return {
            activeColumns: ACTIVE_STATUS_COLUMNS,
            showDoneSeparately: true,
        };
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

        const allowed = new Set([
            ...activeColumns.map((c) => c.key),
            ...(showDoneSeparately && DONE_STATUS_COLUMN ? [DONE_STATUS_COLUMN.key] : []),
        ]);
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
                : (typeof err === 'string' ? err : 'Nepodařilo se změnit stav');
            alert(typeof msg === 'string' && !msg.trim().startsWith('<')
                ? msg
                : 'Nepodařilo se změnit stav');
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

    const renderColumn = (config, extra = {}) => {
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
                {...extra}
            />
        );
    };

    const doneLazyHint = !searchActive && statusFilter !== 'hotovo'
        ? 'Vyřízeno se načte až při hledání (jméno, telefon, model…).'
        : '';

    return (
        <DndContext
            sensors={sensors}
            onDragStart={handleDragStart}
            onDragOver={handleDragOver}
            onDragEnd={handleDragEnd}
        >
            <div className="kanban-board kanban-board--dense">
                <div className="kanban-columns kanban-columns--stacked">
                    {activeColumns.map((config) => renderColumn(config))}

                    {showDoneSeparately && DONE_STATUS_COLUMN && renderColumn(DONE_STATUS_COLUMN, {
                        collapsed: !doneExpanded,
                        onToggleCollapse: () => setDoneExpanded((v) => !v),
                        lazyEmptyHint: doneExpanded ? doneLazyHint : '',
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
