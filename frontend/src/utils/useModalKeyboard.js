import { useEffect } from 'react';

/**
 * ESC zavře modal, Enter odešle formulář (kromě textarea a tlačítek type=button).
 */
export function useModalKeyboard(isOpen, { onClose, formRef }) {
    useEffect(() => {
        if (!isOpen) return undefined;

        const onKeyDown = (e) => {
            if (e.key === 'Escape') {
                e.preventDefault();
                onClose?.();
                return;
            }
            if (e.key !== 'Enter' || e.shiftKey || e.ctrlKey || e.metaKey) return;
            if (e.target.tagName === 'TEXTAREA') return;
            if (e.target.tagName === 'SELECT') return;
            if (e.target.tagName === 'BUTTON' && e.target.type === 'button') return;

            const form = formRef?.current;
            if (form && form.contains(e.target)) {
                e.preventDefault();
                if (typeof form.requestSubmit === 'function') {
                    form.requestSubmit();
                } else {
                    form.dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));
                }
            }
        };

        document.addEventListener('keydown', onKeyDown);
        return () => document.removeEventListener('keydown', onKeyDown);
    }, [isOpen, onClose, formRef]);
}
