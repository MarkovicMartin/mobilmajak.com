import React, { useCallback, useRef, useState } from 'react';
import './FinanceDropZone.css';

const ACCEPT = '.pdf,.jpg,.jpeg,.png,.webp,image/*,application/pdf';

/**
 * Drag & drop + výběr souboru (telefon: galerie / fotoaparát).
 */
const FinanceDropZone = ({
    onFile,
    disabled = false,
    compact = false,
    label = 'Přetáhněte fakturu sem nebo klepněte pro výběr',
}) => {
    const [dragOver, setDragOver] = useState(false);
    const inputRef = useRef(null);

    const pick = useCallback((file) => {
        if (!file || disabled) return;
        onFile?.(file);
    }, [disabled, onFile]);

    const onDragEnter = (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (!disabled) setDragOver(true);
    };

    const onDragLeave = (e) => {
        e.preventDefault();
        e.stopPropagation();
        setDragOver(false);
    };

    const onDragOver = (e) => {
        e.preventDefault();
        e.stopPropagation();
    };

    const onDrop = (e) => {
        e.preventDefault();
        e.stopPropagation();
        setDragOver(false);
        const file = e.dataTransfer?.files?.[0];
        pick(file);
    };

    return (
        <div
            className={`finance-dropzone${dragOver ? ' finance-dropzone--active' : ''}${compact ? ' finance-dropzone--compact' : ''}${disabled ? ' finance-dropzone--disabled' : ''}`}
            onDragEnter={onDragEnter}
            onDragLeave={onDragLeave}
            onDragOver={onDragOver}
            onDrop={onDrop}
            onClick={() => !disabled && inputRef.current?.click()}
            onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    inputRef.current?.click();
                }
            }}
            role="button"
            tabIndex={disabled ? -1 : 0}
            aria-label={label}
        >
            <input
                ref={inputRef}
                type="file"
                accept={ACCEPT}
                capture="environment"
                className="finance-dropzone__input"
                disabled={disabled}
                onChange={(e) => pick(e.target.files?.[0])}
            />
            <span className="finance-dropzone__icon" aria-hidden>📄</span>
            <span className="finance-dropzone__label">{label}</span>
            <span className="finance-dropzone__hint">PDF z mailu, průzkumníku nebo foto ze skeneru</span>
        </div>
    );
};

export default FinanceDropZone;
