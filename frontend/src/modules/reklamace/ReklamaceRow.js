import React, { useRef } from 'react';
import { useDraggable } from '@dnd-kit/core';
import { formatReklamaceDate } from './reklamaceHelpers';
import './ReklamaceRow.css';

const CLICK_DRAG_THRESHOLD_PX = 8;

const ReklamaceRow = ({ item, isDragging = false, onItemClick, onDeleteItem }) => {
    const pointerStart = useRef(null);

    const {
        attributes,
        listeners,
        setNodeRef,
        transform,
        isDragging: isCurrentlyDragging,
    } = useDraggable({
        id: item.id,
    });

    const style = transform
        ? { transform: `translate3d(${transform.x}px, ${transform.y}px, 0)` }
        : undefined;

    const dateSource = item.datum_odeslani || item.created_at || item.datum_vytvoreni;
    const overdueClass = item.is_overdue ? 'reklamace-row--overdue' : '';

    const handlePointerDownCapture = (e) => {
        pointerStart.current = { x: e.clientX, y: e.clientY };
    };

    const handleRowClick = (e) => {
        if (e.target.closest('a, button')) return;
        if (isDragging || isCurrentlyDragging) return;
        const start = pointerStart.current;
        if (start) {
            const dx = Math.abs(e.clientX - start.x);
            const dy = Math.abs(e.clientY - start.y);
            if (dx > CLICK_DRAG_THRESHOLD_PX || dy > CLICK_DRAG_THRESHOLD_PX) return;
        }
        onItemClick(item);
    };

    const cell = (value, title) => (
        <div className="reklamace-row__cell" title={title || value || ''}>
            {value || <span className="reklamace-row__empty">—</span>}
        </div>
    );

    return (
        <div
            ref={setNodeRef}
            style={style}
            className={[
                'reklamace-row',
                isCurrentlyDragging ? 'reklamace-row--placeholder' : '',
                isDragging ? 'reklamace-row--overlay' : '',
                overdueClass,
            ].filter(Boolean).join(' ')}
            onPointerDownCapture={handlePointerDownCapture}
            onClick={handleRowClick}
            {...listeners}
            {...attributes}
        >
            <div className="reklamace-row__cell reklamace-row__datum" title={dateSource || ''}>
                {formatReklamaceDate(dateSource) || <span className="reklamace-row__empty">—</span>}
            </div>
            {cell(item.nase_znacka)}
            {cell(item.nazev_zbozi)}
            {cell(item.dodavatel)}
            {cell(item.faktura)}
            {cell(item.ean)}
            {cell(item.p_kod)}
            {cell(item.cislo_zasilky)}
            {cell(item.prodejna)}
            <div className="reklamace-row__actions">
                <button
                    type="button"
                    className="reklamace-row__btn reklamace-row__btn--delete"
                    title="Skrýt reklamaci"
                    onClick={(e) => {
                        e.stopPropagation();
                        onDeleteItem(item.id);
                    }}
                    onPointerDown={(e) => e.stopPropagation()}
                >
                    Smazat
                </button>
            </div>
        </div>
    );
};

export default ReklamaceRow;
