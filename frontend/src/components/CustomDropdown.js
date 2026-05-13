import React, { useState, useRef, useEffect } from 'react';
import './CustomDropdown.css';

const CustomDropdown = ({ options, value, onChange, placeholder = "Vyberte možnost", className = "" }) => {
    const [isOpen, setIsOpen] = useState(false);
    const [searchTerm, setSearchTerm] = useState('');
    const dropdownRef = useRef(null);
    const searchRef = useRef(null);

    // Filtrované možnosti podle vyhledávání
    const filteredOptions = options.filter(option =>
        option.label.toLowerCase().includes(searchTerm.toLowerCase())
    );

    // Najdi vybranou možnost
    const selectedOption = options.find(option => option.value === value);

    // Uzavři dropdown při kliknutí mimo
    useEffect(() => {
        const handleClickOutside = (event) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
                setIsOpen(false);
                setSearchTerm('');
            }
        };

        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    // Focus na search při otevření
    useEffect(() => {
        if (isOpen && searchRef.current) {
            searchRef.current.focus();
        }
    }, [isOpen]);

    const handleToggle = () => {
        setIsOpen(!isOpen);
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

    return (
        <div className={`custom-dropdown ${className}`} ref={dropdownRef}>
            {/* Trigger button */}
            <button
                type="button"
                className={`dropdown-trigger ${isOpen ? 'open' : ''}`}
                onClick={handleToggle}
                onKeyDown={handleKeyDown}
            >
                <span className="dropdown-value">
                    {selectedOption ? selectedOption.label : placeholder}
                </span>
                <span className={`dropdown-arrow ${isOpen ? 'open' : ''}`}>
                    ▼
                </span>
            </button>

            {/* Dropdown menu */}
            {isOpen && (
                <div className="dropdown-menu">
                    {/* Search box */}
                    {options.length > 8 && (
                        <div className="dropdown-search">
                            <input
                                ref={searchRef}
                                type="text"
                                placeholder="🔍 Hledat..."
                                value={searchTerm}
                                onChange={(e) => setSearchTerm(e.target.value)}
                                onKeyDown={handleKeyDown}
                                className="search-input"
                            />
                        </div>
                    )}
                    
                    {/* Options list */}
                    <div className="dropdown-options">
                        {filteredOptions.length === 0 ? (
                            <div className="dropdown-option disabled">
                                Žádné výsledky
                            </div>
                        ) : (
                            filteredOptions.map((option) => (
                                <button
                                    key={option.value}
                                    type="button"
                                    className={`dropdown-option ${option.value === value ? 'selected' : ''}`}
                                    onClick={() => handleSelect(option)}
                                >
                                    <span className="option-label">{option.label}</span>
                                    {option.value === value && (
                                        <span className="option-check">✓</span>
                                    )}
                                </button>
                            ))
                        )}
                    </div>
                </div>
            )}
        </div>
    );
};

export default CustomDropdown;





