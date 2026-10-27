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
    collapsed = false,
    onToggleCollapse,
    lazyEmptyHint = '',
}) => {
    const { setNodeRef, isOver } = useDroppable({
        id: `column-${id}`,
    });

    const showBody = !collapsed;
    const isLazyEmpty = showBody && orders.length === 0 && lazyEmptyHint;

    return (
        <div
            ref={setNodeRef}
            className={`reklamace-column ${(isOver || isDropTarget) ? 'reklamace-column--drag-over' : ''} ${collapsed ? 'reklamace-column--collapsed' : ''}`}
        >
            <div
                className={`reklamace-column__header${onToggleCollapse ? ' reklamace-column__header--toggle' : ''}`}
                style={{
                    backgroundColor: color,
                    color: textColor,
                }}
                onClick={onToggleCollapse || undefined}
                onKeyDown={onToggleCollapse ? (e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        onToggleCollapse();
                    }
                } : undefined}
                role={onToggleCollapse ? 'button' : undefined}
                tabIndex={onToggleCollapse ? 0 : undefined}
                aria-expanded={onToggleCollapse ? !collapsed : undefined}
            >
                <div className="reklamace-column__header-content">
                    {onToggleCollapse && (
                        <span className="reklamace-column__chevron" aria-hidden="true">
                            {collapsed ? '▸' : '▾'}
                        </span>
                    )}
                    <span className="reklamace-column__title">{title}</span>
                    <span className="reklamace-column__count">({count})</span>
                </div>
            </div>

            {showBody && (
            <div className="reklamace-column__content">
                <div className="reklamace-row-header" aria-hidden="true">
                    {ROW_HEADERS.map((label, i) => (
                        <span key={`${label}-${i}`}>{label}</span>
                    ))}
                </div>

                {isLazyEmpty ? (
                    <div className="reklamace-column__empty">
                        <p>{lazyEmptyHint}</p>
                    </div>
                ) : orders.length === 0 ? (
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
            )}

            {(isOver || isDropTarget) && (
                <div className="reklamace-column__drop-indicator" aria-hidden="true" />
            )}
        </div>
    );
};

export default ReklamaceColumn;
