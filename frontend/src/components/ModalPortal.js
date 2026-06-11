import { createPortal } from 'react-dom';

/**
 * Vykreslí modál na document.body – mimo stacking context modulů (analytics, orders…).
 */
function ModalPortal({ children }) {
    if (typeof document === 'undefined') return null;
    return createPortal(children, document.body);
}

export default ModalPortal;
