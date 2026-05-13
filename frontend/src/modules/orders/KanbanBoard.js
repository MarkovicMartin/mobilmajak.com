import React, { useState } from 'react';
import {
    DndContext,
    DragOverlay,
    useSensor,
    useSensors,
    PointerSensor,
    KeyboardSensor,
    TouchSensor
} from '@dnd-kit/core';
import { sortableKeyboardCoordinates } from '@dnd-kit/sortable';
import OrderCard from './OrderCard';
import KanbanColumn from './KanbanColumn';
import './KanbanBoard.css';

const KanbanBoard = ({ 
    kanbanData, 
    onStatusChange, 
    onOrderClick, 
    onDeleteOrder,
    loading 
}) => {
    const [activeOrder, setActiveOrder] = useState(null);
    const [dragOverColumn, setDragOverColumn] = useState(null);

    // Nastavení sensorů pro drag & drop
    const sensors = useSensors(
        useSensor(PointerSensor, {
            activationConstraint: {
                distance: 8,
            },
        }),
        useSensor(TouchSensor, {
            activationConstraint: {
                delay: 250,
                tolerance: 8,
            },
        }),
        useSensor(KeyboardSensor, {
            coordinateGetter: sortableKeyboardCoordinates,
        })
    );

    // Definice stavů a jejich barev
    const statusConfig = {
        'nove': { 
            label: 'Nové', 
            color: '#ffeb3b', 
            icon: '🆕',
            textColor: '#000'
        },
        'objednano': { 
            label: 'Objednáno', 
            color: '#2196f3', 
            icon: '📋',
            textColor: '#fff'
        },
        'v_kosiku': { 
            label: 'V košíku', 
            color: '#ff9800', 
            icon: '🛒',
            textColor: '#000'
        },
        'predobjednano': { 
            label: 'Předobjednáno', 
            color: '#9c27b0', 
            icon: '⏳',
            textColor: '#fff'
        },
        'neni_skladem': { 
            label: 'Není skladem', 
            color: '#f44336', 
            icon: '❌',
            textColor: '#fff'
        },
        'storno': { 
            label: 'Storno', 
            color: '#757575', 
            icon: '🚫',
            textColor: '#fff'
        },
        'dorazilo_ceka': { 
            label: 'Dorazilo čeká na zákazníka', 
            color: '#4caf50', 
            icon: '📦',
            textColor: '#fff'
        },
        'hotovo': { 
            label: 'Hotovo', 
            color: '#8bc34a', 
            icon: '✅',
            textColor: '#000'
        }
    };

    // Začátek tažení
    const handleDragStart = (event) => {
        const { active } = event;
        const orderId = active.id;
        
        // Najdeme objednávku v datech
        let foundOrder = null;
        if (kanbanData && Object.keys(kanbanData).length > 0) {
            Object.values(kanbanData).forEach(column => {
                if (column && column.orders) {
                    const order = column.orders.find(o => o.id === orderId);
                    if (order) {
                        foundOrder = order;
                    }
                }
            });
        }
        
        setActiveOrder(foundOrder);
    };

    // Tažení nad sloupcem
    const handleDragOver = (event) => {
        const { over } = event;
        
        if (over) {
            const overColumn = over.id.startsWith('column-') 
                ? over.id.replace('column-', '') 
                : null;
            setDragOverColumn(overColumn);
        } else {
            setDragOverColumn(null);
        }
    };

    // Ukončení tažení
    const handleDragEnd = async (event) => {
        const { active, over } = event;
        
        setActiveOrder(null);
        setDragOverColumn(null);

        if (!over) return;

        const orderId = active.id;
        let newStatus = null;

        // Zjistíme cílový sloupec
        if (over.id.startsWith('column-')) {
            newStatus = over.id.replace('column-', '');
        } else {
            // Přetaženo na jinou kartu - zjistíme ve kterém sloupci se nachází
            if (kanbanData && Object.keys(kanbanData).length > 0) {
                Object.keys(kanbanData).forEach(status => {
                    const statusData = kanbanData[status];
                    if (statusData && statusData.orders) {
                        const orders = statusData.orders;
                        if (orders.find(o => o.id === over.id)) {
                            newStatus = status;
                        }
                    }
                });
            }
        }

        if (newStatus && activeOrder && activeOrder.status !== newStatus) {
            const result = await onStatusChange(orderId, newStatus);
            if (!result.success) {
                alert(result.error);
            }
        }
    };

    if (loading && (!kanbanData || Object.keys(kanbanData).length === 0)) {
        return (
            <div className="kanban-board">
                <div className="loading-board">
                    <div className="spinner"></div>
                    <p>Načítám kanban board...</p>
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
            <div className="kanban-board">
                <div className="kanban-columns">
                    {Object.keys(statusConfig).map(statusKey => {
                        const config = statusConfig[statusKey];
                        const columnData = (kanbanData && kanbanData[statusKey]) || { orders: [], count: 0 };
                        const isDropTarget = dragOverColumn === statusKey;
                        
                        return (
                            <KanbanColumn
                                key={statusKey}
                                id={statusKey}
                                title={config.label}
                                icon={config.icon}
                                color={config.color}
                                textColor={config.textColor}
                                orders={columnData.orders}
                                count={columnData.count}
                                isDropTarget={isDropTarget}
                                onOrderClick={onOrderClick}
                                onDeleteOrder={onDeleteOrder}
                            />
                        );
                    })}
                </div>

                {/* Drag overlay */}
                <DragOverlay>
                    {activeOrder ? (
                        <OrderCard 
                            order={activeOrder}
                            isDragging={true}
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