import React from 'react';
import Modal from './Modal';

/**
 * Potvrzovací dialog – stejná šablona jako ostatní modály.
 */
function ConfirmModal({
    onClose,
    onConfirm,
    title,
    children,
    confirmLabel = 'Potvrdit',
    cancelLabel = 'Zrušit',
    confirmVariant = 'danger',
    confirmDisabled = false,
}) {
    const confirmClass = confirmVariant === 'danger' ? 'btn-delete' : 'btn-submit';

    return (
        <Modal
            onClose={onClose}
            title={title}
            size="sm"
            footer={(
                <>
                    <button type="button" className="btn-cancel" onClick={onClose}>
                        {cancelLabel}
                    </button>
                    <button
                        type="button"
                        className={confirmClass}
                        onClick={onConfirm}
                        disabled={confirmDisabled}
                    >
                        {confirmLabel}
                    </button>
                </>
            )}
        >
            {children}
        </Modal>
    );
}

export default ConfirmModal;
