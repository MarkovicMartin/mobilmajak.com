import React from 'react';
import ModalPortal from '../ModalPortal';
import { useModalKeyboard } from '../../utils/useModalKeyboard';
import './Modal.css';

const SIZE_CLASS = {
    sm: 'modal-content--sm',
    md: 'modal-content--md',
    lg: 'modal-content--lg',
};

/**
 * Jednotná šablona modálního okna – overlay, hlavička, scrollovatelné tělo, patička.
 */
function Modal({
    onClose,
    title,
    titleId,
    titleAs: TitleTag = 'h2',
    size = 'md',
    children,
    footer,
    bodyClassName = '',
    contentClassName = '',
    formRef,
    onSubmit,
    closeOnBackdrop = true,
}) {
    useModalKeyboard(true, { onClose, formRef });

    const handleBackdrop = (e) => {
        if (closeOnBackdrop && e.target === e.currentTarget) {
            onClose?.();
        }
    };

    const resolvedTitleId = titleId || (title != null && title !== false ? 'modal-title' : undefined);

    const inner = (
        <>
            {title != null && title !== false && (
                <div className="modal-header ui-modal__header">
                    <TitleTag id={resolvedTitleId} className="modal-title ui-modal__title">
                        {title}
                    </TitleTag>
                    {onClose && (
                        <button
                            type="button"
                            className="modal-close ui-modal__close"
                            onClick={onClose}
                            aria-label="Zavřít"
                        >
                            ✕
                        </button>
                    )}
                </div>
            )}
            <div className={['modal-body', 'ui-modal__body', bodyClassName].filter(Boolean).join(' ')}>
                {children}
            </div>
            {footer != null && (
                <div className="modal-footer ui-modal__footer">{footer}</div>
            )}
        </>
    );

    const contentClass = [
        'modal-content',
        'ui-modal__content',
        SIZE_CLASS[size] || SIZE_CLASS.md,
        contentClassName,
    ]
        .filter(Boolean)
        .join(' ');

    return (
        <ModalPortal>
            <div
                className="modal-overlay ui-modal__overlay"
                onClick={handleBackdrop}
                role="presentation"
            >
                <div
                    className={contentClass}
                    onClick={(e) => e.stopPropagation()}
                    role="dialog"
                    aria-modal="true"
                    aria-labelledby={resolvedTitleId}
                >
                    {onSubmit ? (
                        <form ref={formRef} className="modal-form ui-modal__form" onSubmit={onSubmit} noValidate>
                            {inner}
                        </form>
                    ) : (
                        inner
                    )}
                </div>
            </div>
        </ModalPortal>
    );
}

export default Modal;
