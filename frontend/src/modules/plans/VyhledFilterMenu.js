import React, { useEffect, useRef } from 'react';

/**
 * Rozbalovací panel – změny se aplikují až při zavření (klik mimo / Enter).
 * Escape = zrušit bez aplikace.
 */
export default function VyhledFilterMenu({
  open,
  onClose,
  triggerLabel,
  onTriggerClick,
  children,
  className = '',
  title,
}) {
  const ref = useRef(null);

  useEffect(() => {
    if (!open) return undefined;
    const onMouseDown = (e) => {
      if (ref.current && !ref.current.contains(e.target)) {
        onClose(true);
      }
    };
    document.addEventListener('mousedown', onMouseDown);
    return () => document.removeEventListener('mousedown', onMouseDown);
  }, [open, onClose]);

  useEffect(() => {
    if (!open) return undefined;
    const onKeyDown = (e) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        onClose(false);
      } else if (e.key === 'Enter' && ref.current?.contains(document.activeElement)) {
        const tag = document.activeElement?.tagName;
        if (tag !== 'INPUT' && tag !== 'TEXTAREA') {
          e.preventDefault();
          onClose(true);
        }
      }
    };
    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, [open, onClose]);

  return (
    <div className={`plans-vyhled-dropdown ${className}${open ? ' is-open' : ''}`} ref={ref}>
      <button
        type="button"
        className="plans-vyhled-dropdown-trigger"
        onClick={onTriggerClick}
        aria-expanded={open}
        title={title}
      >
        <span className="plans-vyhled-dropdown-label">{triggerLabel}</span>
        <span className="plans-vyhled-dropdown-caret" aria-hidden="true">{open ? '▲' : '▼'}</span>
      </button>
      {open && (
        <div className="plans-vyhled-dropdown-panel" role="dialog" aria-label={title}>
          {children}
          <p className="plans-vyhled-dropdown-hint">Enter nebo klik mimo = použít · Esc = zrušit</p>
        </div>
      )}
    </div>
  );
}
