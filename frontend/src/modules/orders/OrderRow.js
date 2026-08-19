import React, { useRef, useState } from 'react';
import { useDraggable } from '@dnd-kit/core';
import { copyToClipboard } from '../../utils/clipboard';
import {
    formatOrderDate,
    formatZadal,
    formatProdejna,
    myrepairUrl,
    orderAgeClass,
} from './orderHelpers';
import './OrderRow.css';

const CLICK_DRAG_THRESHOLD_PX = 8;
const NOTE_BUBBLE_MAX_W = 320;
const NOTE_BUBBLE_GAP = 8;

const OrderRow = ({ order, isDragging = false, onOrderClick, onDeleteOrder }) => {
    const pointerStart = useRef(null);
    const [phoneCopied, setPhoneCopied] = useState(false);
    const [noteBubble, setNoteBubble] = useState(null);

    const {
        attributes,
        listeners,
        setNodeRef,
        transform,
        isDragging: isCurrentlyDragging,
    } = useDraggable({
        id: order.id,
    });

    const style = transform
        ? { transform: `translate3d(${transform.x}px, ${transform.y}px, 0)` }
        : undefined;

    const priorityClass = orderAgeClass(order);

    const repairLink = myrepairUrl(order.servisni_cislo);
    const customer = `${order.jmeno_zakaznika || ''} ${order.prijmeni_zakaznika || ''}`.trim();
    const noteText = (order.poznamka || '').trim();

    const handlePointerDownCapture = (e) => {
        pointerStart.current = { x: e.clientX, y: e.clientY };
    };

    const handleRowClick = (e) => {
        if (e.target.closest('a, button, .order-row__note')) return;
        if (isDragging || isCurrentlyDragging) return;
        const start = pointerStart.current;
        if (start) {
            const dx = Math.abs(e.clientX - start.x);
            const dy = Math.abs(e.clientY - start.y);
            if (dx > CLICK_DRAG_THRESHOLD_PX || dy > CLICK_DRAG_THRESHOLD_PX) return;
        }
        onOrderClick(order);
    };

    const showNoteBubble = (e) => {
        const rect = e.currentTarget.getBoundingClientRect();
        const width = Math.min(NOTE_BUBBLE_MAX_W, window.innerWidth - 16);
        let left = rect.right - width;
        if (left < 8) left = 8;
        const placeBelow = rect.top < 120;
        setNoteBubble({
            left,
            width,
            ...(placeBelow
                ? { top: rect.bottom + NOTE_BUBBLE_GAP }
                : { bottom: window.innerHeight - rect.top + NOTE_BUBBLE_GAP }),
            placeBelow,
        });
    };

    return (
        <div
            ref={setNodeRef}
            style={style}
            className={`order-row ${isCurrentlyDragging ? 'order-row--placeholder' : ''} ${isDragging ? 'order-row--overlay' : ''} ${priorityClass}`}
            onPointerDownCapture={handlePointerDownCapture}
            onClick={handleRowClick}
            {...listeners}
            {...attributes}
        >
            <div className="order-row__cell order-row__datum" title={order.datum_vytvoreni}>
                {formatOrderDate(order.datum_vytvoreni)}
            </div>
            <div className="order-row__cell order-row__typ" title={order.typ_telefonu}>
                {order.typ_telefonu}
            </div>
            <div className="order-row__cell order-row__dil" title={order.dil}>
                {order.dil}
            </div>
            <div className="order-row__cell order-row__barva" title={order.barva || ''}>
                {order.barva || ''}
            </div>
            <div className="order-row__cell order-row__serviska">
                {repairLink ? (
                    <a
                        className="order-chip order-chip--link"
                        href={repairLink}
                        target="_blank"
                        rel="noopener noreferrer"
                        title="Otevřít v MyRepair"
                        onClick={(e) => e.stopPropagation()}
                        onPointerDown={(e) => e.stopPropagation()}
                    >
                        {order.servisni_cislo}
                    </a>
                ) : order.servisni_cislo ? (
                    <span className="order-chip">{order.servisni_cislo}</span>
                ) : (
                    <span className="order-row__empty">—</span>
                )}
            </div>
            <div className="order-row__cell order-row__zakaznik" title={customer}>
                {customer || '—'}
            </div>
            <div className="order-row__cell order-row__telefon">
                {order.telefon_zakaznika ? (
                    <button
                        type="button"
                        className={`order-chip order-chip--copy${phoneCopied ? ' order-chip--copied' : ''}`}
                        title={phoneCopied ? 'Zkopírováno' : 'Klikněte pro zkopírování'}
                        onClick={async (e) => {
                            e.stopPropagation();
                            const result = await copyToClipboard(order.telefon_zakaznika);
                            if (result.success) {
                                setPhoneCopied(true);
                                window.setTimeout(() => setPhoneCopied(false), 1200);
                            }
                        }}
                        onPointerDown={(e) => e.stopPropagation()}
                    >
                        {order.telefon_zakaznika}
                    </button>
                ) : (
                    <span className="order-row__empty">—</span>
                )}
            </div>
            <div className="order-row__cell order-row__cena">
                {order.cena != null && order.cena !== ''
                    ? parseFloat(order.cena).toLocaleString('cs-CZ')
                    : ''}
            </div>
            <div className="order-row__cell order-row__zadal" title={formatZadal(order.zalozil)}>
                {formatZadal(order.zalozil)}
            </div>
            <div className="order-row__cell order-row__prodejna" title={formatProdejna(order.prodejna)}>
                {formatProdejna(order.prodejna)}
            </div>
            <div className="order-row__cell order-row__dodavatel" title={order.dodavatel || ''}>
                {order.dodavatel || ''}
            </div>
            <div className="order-row__actions">
                {noteText ? (
                    <span
                        className="order-row__note"
                        aria-label="Poznámka k objednávce"
                        onClick={(e) => e.stopPropagation()}
                        onPointerDown={(e) => e.stopPropagation()}
                        onMouseEnter={showNoteBubble}
                        onMouseLeave={() => setNoteBubble(null)}
                        onFocus={showNoteBubble}
                        onBlur={() => setNoteBubble(null)}
                        tabIndex={0}
                    >
                        <span className="order-row__note-icon" aria-hidden="true">📝</span>
                        {noteBubble ? (
                            <span
                                className={`order-row__note-bubble${noteBubble.placeBelow ? ' order-row__note-bubble--below' : ''}`}
                                role="tooltip"
                                style={{
                                    left: noteBubble.left,
                                    width: noteBubble.width,
                                    ...(noteBubble.placeBelow
                                        ? { top: noteBubble.top }
                                        : { bottom: noteBubble.bottom }),
                                }}
                            >
                                {noteText}
                            </span>
                        ) : null}
                    </span>
                ) : (
                    <span
                        className="order-row__note order-row__note--placeholder"
                        aria-hidden="true"
                    />
                )}
                <button
                    type="button"
                    className="order-row__btn order-row__btn--delete"
                    title="Smazat"
                    aria-label="Smazat"
                    onClick={(e) => {
                        e.stopPropagation();
                        onDeleteOrder(order.id);
                    }}
                    onPointerDown={(e) => e.stopPropagation()}
                >
                    ✕
                </button>
            </div>
        </div>
    );
};

export default OrderRow;
