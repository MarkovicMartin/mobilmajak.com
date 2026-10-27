import React, { useEffect, useState } from 'react';
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
import ReklamaceRow from './ReklamaceRow';
import ReklamaceColumn from './ReklamaceColumn';
import {
    ACTIVE_STATUS_COLUMNS,
    DONE_STATUS_COLUMN,
    STATUS_COLUMNS,
    STATUS_KEYS,
    canTransition,
    promptZpusobVyrizeni,
    REKLAMACE_STATUS,
} from './reklamaceHelpers';
import './ReklamaceBoard.css';

const ReklamaceBoard = ({
    kanbanData,
    onStatusChange,
    onItemClick,
    onDeleteItem,
    loading,
    statusFilter = '',
    searchActive = false,
}) => {
    const [activeItem, setActiveItem] = useState(null);
    const [dragOverColumn, setDragOverColumn] = useState(null);
    const [doneExpanded, setDoneExpanded] = useState(false);

    useEffect(() => {
        if (searchActive || statusFilter === REKLAMACE_STATUS.VRIZENE) {
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
        }),
    );

    const { activeColumns, showDoneSeparately } = (() => {
        if (statusFilter === REKLAMACE_STATUS.VRIZENE) {
            return { activeColumns: [], showDoneSeparately: true };
        }
        if (statusFilter && STATUS_KEYS.includes(statusFilter)) {
            return {
                activeColumns: STATUS_COLUMNS.filter((c) => c.key === statusFilter),
                showDoneSeparately: false,
            };
        }
        return {
            activeColumns: ACTIVE_STATUS_COLUMNS,
            showDoneSeparately: true,
        };
    })();

    const handleDragStart = (event) => {
        const itemId = event.active.id;
        let found = null;
        if (kanbanData) {
            Object.values(kanbanData).forEach((column) => {
                const hit = column?.orders?.find((o) => o.id === itemId);
                if (hit) found = hit;
            });
        }
        setActiveItem(found);
    };

    const handleDragOver = (event) => {
        const { over } = event;
        if (over?.id?.startsWith?.('column-')) {
            setDragOverColumn(String(over.id).replace('column-', ''));
        } else {
            setDragOverColumn(null);
        }
    };

    const handleDragEnd = async (event) => {
        const { active, over } = event;
        setActiveItem(null);
        setDragOverColumn(null);
        if (!over) return;

        const itemId = active.id;
        let newStatus = null;

        if (String(over.id).startsWith('column-')) {
            newStatus = String(over.id).replace('column-', '');
        } else if (kanbanData) {
            Object.keys(kanbanData).forEach((status) => {
                if (kanbanData[status]?.orders?.find((o) => o.id === over.id)) {
                    newStatus = status;
                }
            });
        }

        if (!newStatus || !activeItem || activeItem.status === newStatus) {
            return;
        }

        const allowedCols = new Set([
            ...activeColumns.map((c) => c.key),
            ...(showDoneSeparately && DONE_STATUS_COLUMN ? [DONE_STATUS_COLUMN.key] : []),
        ]);
        if (!allowedCols.has(newStatus)) return;

        if (!canTransition(activeItem.status, newStatus)) {
            alert('Tento přechod není povolen (jen dopředu: Nezpracované → Odeslané → Vyřízené).');
            return;
        }

        let zpusob = null;
        if (newStatus === REKLAMACE_STATUS.VRIZENE) {
            zpusob = promptZpusobVyrizeni();
            if (!zpusob) {
                alert('Způsob vyřízení je povinný.');
                return;
            }
        }

        const result = await onStatusChange(itemId, newStatus, { zpusob_vyrizeni: zpusob });
        if (!result?.success) {
            const err = result?.error;
            const msg = typeof err === 'object'
                ? (err.detail || err.error || JSON.stringify(err))
                : (err || 'Přesun selhal');
            alert(msg);
        }
    };

    if (loading && (!kanbanData || Object.keys(kanbanData).length === 0)) {
        return (
            <div className="reklamace-board">
                <div className="reklamace-board__loading">
                    <div className="spinner" />
                    <p>Načítám reklamace…</p>
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
            <div className="reklamace-board">
                <div className="reklamace-board__columns">
                    {activeColumns.map((config) => {
                        const columnData = (kanbanData && kanbanData[config.key]) || {
                            orders: [],
                            count: 0,
                        };
                        return (
                            <ReklamaceColumn
                                key={config.key}
                                id={config.key}
                                title={config.label}
                                color={config.color}
                                textColor={config.textColor}
                                orders={columnData.orders || []}
                                count={columnData.count || 0}
                                isDropTarget={dragOverColumn === config.key}
                                onItemClick={onItemClick}
                                onDeleteItem={onDeleteItem}
                            />
                        );
                    })}
                    {showDoneSeparately && DONE_STATUS_COLUMN && (() => {
                        const columnData = (kanbanData && kanbanData[DONE_STATUS_COLUMN.key]) || {
                            orders: [],
                            count: 0,
                        };
                        const doneLazyHint = !searchActive && statusFilter !== REKLAMACE_STATUS.VRIZENE
                            ? 'Vyřízené se načtou až při hledání (značka, název, EAN, zásilka…).'
                            : '';
                        return (
                            <ReklamaceColumn
                                key={DONE_STATUS_COLUMN.key}
                                id={DONE_STATUS_COLUMN.key}
                                title={DONE_STATUS_COLUMN.label}
                                color={DONE_STATUS_COLUMN.color}
                                textColor={DONE_STATUS_COLUMN.textColor}
                                orders={columnData.orders || []}
                                count={columnData.count || 0}
                                isDropTarget={dragOverColumn === DONE_STATUS_COLUMN.key}
                                onItemClick={onItemClick}
                                onDeleteItem={onDeleteItem}
                                collapsed={!doneExpanded}
                                onToggleCollapse={() => setDoneExpanded((v) => !v)}
                                lazyEmptyHint={doneExpanded ? doneLazyHint : ''}
                            />
                        );
                    })()}
                </div>

                <DragOverlay>
                    {activeItem ? (
                        <ReklamaceRow
                            item={activeItem}
                            isDragging
                            onItemClick={() => {}}
                            onDeleteItem={() => {}}
                        />
                    ) : null}
                </DragOverlay>
            </div>
        </DndContext>
    );
};

export default ReklamaceBoard;
