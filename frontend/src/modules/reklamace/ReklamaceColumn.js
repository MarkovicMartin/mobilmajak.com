import React from 'react';
import { useDroppable } from '@dnd-kit/core';
import ReklamaceRow from './ReklamaceRow';
import './ReklamaceColumn.css';
import './ReklamaceRow.css';

const ROW_HEADERS = [
    'Datum', 'Značka', 'Název', 'Dodavatel', 'Faktura',
    'EAN', 'P', 'Zásilka', 'Prodejna', '',
];

const ReklamaceColumn = ({
    id,
    title,
    color,
    textColor,
    orders,
    count,
    isDropTarget,
    onItemClick,
    onDeleteItem,
}) => {
    const { setNodeRef, isOver } = useDroppable({
        id: `column-${id}`,
    });

    return (
        <div
            ref={setNodeRef}
            className={`reklamace-column ${(isOver || isDropTarget) ? 'reklamace-column--drag-over' : ''}`}
        >
            <div
                className="reklamace-column__header"
                style={{
                    backgroundColor: color,
                    color: textColor,
                }}
            >
                <div className="reklamace-column__header-content">
                    <span className="reklamace-column__title">{title}</span>
                    <span className="reklamace-column__count">({count})</span>
                </div>
            </div>

            <div className="reklamace-column__content">
                <div className="reklamace-row-header" aria-hidden="true">
                    {ROW_HEADERS.map((label, i) => (
                        <span key={`${label}-${i}`}>{label}</span>
                    ))}
                </div>

                {orders.length === 0 ? (
                    <div className="reklamace-column__empty">
                        <p>Žádné reklamace</p>
                    </div>
                ) : (
                    <div className="reklamace-column__list">
                        {orders.map((item) => (
                            <ReklamaceRow
                                key={item.id}
                                item={item}
                                onItemClick={onItemClick}
                                onDeleteItem={onDeleteItem}
                            />
                        ))}
                    </div>
                )}
            </div>

            {(isOver || isDropTarget) && (
                <div className="reklamace-column__drop-indicator" aria-hidden="true" />
            )}
        </div>
    );
};

export default ReklamaceColumn;
