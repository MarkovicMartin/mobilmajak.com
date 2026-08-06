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

const OrderRow = ({ order, isDragging = false, onOrderClick, onDeleteOrder }) => {
    const pointerStart = useRef(null);
    const [phoneCopied, setPhoneCopied] = useState(false);

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
        onOrderClick(order);
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
                <button
                    type="button"
                    className="order-row__btn order-row__btn--delete"
                    title="Smazat objednávku"
                    onClick={(e) => {
                        e.stopPropagation();
                        onDeleteOrder(order.id);
                    }}
                    onPointerDown={(e) => e.stopPropagation()}
                >
                    Smazat
                </button>
            </div>
        </div>
    );
};

export default OrderRow;
