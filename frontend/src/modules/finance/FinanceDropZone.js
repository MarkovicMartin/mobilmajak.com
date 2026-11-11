import React, { useCallback, useRef, useState } from 'react';
import './FinanceDropZone.css';

const ACCEPT = '.pdf,.jpg,.jpeg,.png,.webp,image/*,application/pdf';

/**
 * Drag & drop + výběr souboru (telefon: galerie / fotoaparát).
 */
const FinanceDropZone = ({
    onFile,
    onFiles,
    multiple = false,
    disabled = false,
    compact = false,
    label = 'Přetáhněte fakturu sem nebo klepněte pro výběr',
}) => {
    const [dragOver, setDragOver] = useState(false);
    const inputRef = useRef(null);

    const deliver = useCallback((list) => {
        const files = Array.from(list || []).filter(Boolean);
        if (!files.length || disabled) return;
        if (multiple && onFiles) onFiles(files);
        else onFile?.(files[0]);
    }, [disabled, multiple, onFile, onFiles]);

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
        deliver(e.dataTransfer?.files);
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
                multiple={multiple}
                capture={multiple ? undefined : 'environment'}
                className="finance-dropzone__input"
                disabled={disabled}
                onChange={(e) => {
                    deliver(e.target.files);
                    e.target.value = '';
                }}
            />
            <span className="finance-dropzone__icon" aria-hidden>📄</span>
            <span className="finance-dropzone__label">{label}</span>
            <span className="finance-dropzone__hint">PDF z mailu, průzkumníku nebo foto ze skeneru</span>
        </div>
    );
};

export default FinanceDropZone;
