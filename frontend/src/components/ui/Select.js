import React, { useState, useRef, useEffect, useLayoutEffect, useCallback } from 'react';
import { createPortal } from 'react-dom';
import './Select.css';

const SEARCH_THRESHOLD = 8;

/**
 * Vlastní select s portálem – volitelné vyhledávání.
 * legacy=true používá třídy custom-dropdown pro zpětnou kompatibilitu.
 */
const Select = ({
    options = [],
    value,
    onChange,
    placeholder = 'Vyberte možnost',
    searchable,
    searchPlaceholder = 'Hledat…',
    className = '',
    disabled = false,
    legacy = false,
    id,
    'aria-label': ariaLabel,
}) => {
    const [isOpen, setIsOpen] = useState(false);
    const [searchTerm, setSearchTerm] = useState('');
    const [menuStyle, setMenuStyle] = useState({});
    const rootRef = useRef(null);
    const triggerRef = useRef(null);
    const menuRef = useRef(null);
    const searchRef = useRef(null);

    const showSearch = searchable ?? options.length > SEARCH_THRESHOLD;

    const filteredOptions = options.filter((option) =>
        option.label.toLowerCase().includes(searchTerm.toLowerCase())
    );

    const selectedOption = options.find((option) => option.value === value);

    const rootClass = legacy
        ? `custom-dropdown ${className}`.trim()
        : `ui-select ${className}`.trim();
    const triggerClass = legacy
        ? `dropdown-trigger${isOpen ? ' open' : ''}`
        : `ui-select__trigger${isOpen ? ' ui-select__trigger--open' : ''}`;
    const valueClass = legacy ? 'dropdown-value' : 'ui-select__value';
    const arrowClass = legacy
        ? `dropdown-arrow${isOpen ? ' open' : ''}`
        : `ui-select__arrow${isOpen ? ' ui-select__arrow--open' : ''}`;
    const menuClass = legacy ? 'dropdown-menu' : 'ui-select__menu';
    const searchWrapClass = legacy ? 'dropdown-search' : 'ui-select__search';
    const searchInputClass = legacy ? 'search-input' : 'ui-select__search-input input';
    const optionsClass = legacy ? 'dropdown-options' : 'ui-select__options';
    const optionClass = (selected) => {
        if (legacy) {
            return `dropdown-option${selected ? ' selected' : ''}`;
        }
        return `ui-select__option${selected ? ' ui-select__option--selected' : ''}`;
    };
    const emptyClass = legacy ? 'dropdown-option disabled' : 'ui-select__option ui-select__option--empty';
    const checkClass = legacy ? 'option-check' : 'ui-select__check';
    const labelClass = legacy ? 'option-label' : 'ui-select__option-label';

    const usePortal = !legacy;

    const updateMenuPosition = useCallback(() => {
        const trigger = triggerRef.current;
        if (!trigger || !usePortal) return;
        const rect = trigger.getBoundingClientRect();

        // Select menu se renderuje přes portal na `document.body`.
        // Když je trigger uvnitř modalu, overlay modalu má často vyšší `z-index`
        // (např. `.modal-overlay { z-index: ... !important; } v `App.css`),
        // takže menu jinak spadne "pod" modal.
        let zIndex = 1500;
        const overlayEl = rootRef.current?.closest?.('.modal-overlay, .task-modal-overlay');
        if (overlayEl) {
            const parsed = Number.parseInt(window.getComputedStyle(overlayEl).zIndex, 10);
            if (!Number.isNaN(parsed)) zIndex = parsed + 10;
        }

        setMenuStyle({
            position: 'fixed',
            top: rect.bottom + 4,
            left: rect.left,
            width: rect.width,
            zIndex,
        });
    }, [usePortal, rootRef]);

    useLayoutEffect(() => {
        if (!isOpen || !usePortal) return undefined;
        updateMenuPosition();
        const onScrollOrResize = () => updateMenuPosition();
        window.addEventListener('scroll', onScrollOrResize, true);
        window.addEventListener('resize', onScrollOrResize);
        return () => {
            window.removeEventListener('scroll', onScrollOrResize, true);
            window.removeEventListener('resize', onScrollOrResize);
        };
    }, [isOpen, usePortal, updateMenuPosition]);

    useEffect(() => {
        if (!isOpen) return undefined;
        const handleClickOutside = (event) => {
            const inRoot = rootRef.current?.contains(event.target);
            const inMenu = menuRef.current?.contains(event.target);
            if (!inRoot && !inMenu) {
                setIsOpen(false);
                setSearchTerm('');
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, [isOpen]);

    useEffect(() => {
        if (isOpen && showSearch && searchRef.current) {
            searchRef.current.focus();
        }
    }, [isOpen, showSearch]);

    const handleToggle = () => {
        if (disabled) return;
        setIsOpen((prev) => !prev);
        setSearchTerm('');
    };

    const handleSelect = (option) => {
        onChange(option.value);
        setIsOpen(false);
        setSearchTerm('');
    };

    const handleKeyDown = (e) => {
        if (e.key === 'Escape') {
            setIsOpen(false);
            setSearchTerm('');
        } else if (e.key === 'Enter' && filteredOptions.length === 1) {
            handleSelect(filteredOptions[0]);
        }
    };

    const menuContent = isOpen ? (
        <div
            ref={menuRef}
            className={menuClass}
            style={usePortal ? menuStyle : undefined}
            role="listbox"
            id={id ? `${id}-listbox` : undefined}
        >
            {showSearch && (
                <div className={searchWrapClass}>
                    <input
                        ref={searchRef}
                        type="text"
                        placeholder={searchPlaceholder}
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        onKeyDown={handleKeyDown}
                        className={searchInputClass}
                        aria-label={searchPlaceholder}
                    />
                </div>
            )}
            <div className={optionsClass}>
                {filteredOptions.length === 0 ? (
                    <div className={emptyClass} role="option" aria-selected={false} aria-disabled="true">
                        Žádné výsledky
                    </div>
                ) : (
                    filteredOptions.map((option) => (
                        <button
                            key={option.value}
                            type="button"
                            role="option"
                            aria-selected={option.value === value}
                            className={optionClass(option.value === value)}
                            onClick={() => handleSelect(option)}
                        >
                            <span className={labelClass}>{option.label}</span>
                            {option.value === value && (
                                <span className={checkClass} aria-hidden="true">
                                    ✓
                                </span>
                            )}
                        </button>
                    ))
                )}
            </div>
        </div>
    ) : null;

    const menu = usePortal && menuContent ? createPortal(menuContent, document.body) : menuContent;

    return (
        <div className={rootClass} ref={rootRef}>
            <button
                ref={triggerRef}
                id={id}
                type="button"
                className={triggerClass}
                onClick={handleToggle}
                onKeyDown={handleKeyDown}
                disabled={disabled}
                aria-haspopup="listbox"
                aria-expanded={isOpen}
                aria-label={ariaLabel}
            >
                <span className={valueClass}>
                    {selectedOption ? selectedOption.label : placeholder}
                </span>
                <span className={arrowClass} aria-hidden="true">
                    ▼
                </span>
            </button>
            {menu}
        </div>
    );
};

export default Select;
