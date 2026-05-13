import React, { useState, useRef, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { useNavigate, useLocation } from 'react-router-dom';
import './AdminDropdown.css';

const AdminDropdown = ({ onOpen }) => {
    const [isOpen, setIsOpen] = useState(false);
    const dropdownRef = useRef(null);
    const mobileDrawerRef = useRef(null);
    const navigate = useNavigate();
    const location = useLocation();

    useEffect(() => {
        const handleClickOutside = (event) => {
            const inToggle = dropdownRef.current?.contains(event.target);
            const inDrawer = mobileDrawerRef.current?.contains(event.target);
            if (inToggle || inDrawer) return;
            setIsOpen(false);
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    useEffect(() => {
        setIsOpen(false);
    }, [location.pathname]);

    useEffect(() => {
        if (isOpen) {
            document.body.style.overflow = 'hidden';
            const handleEscape = (e) => { if (e.key === 'Escape') setIsOpen(false); };
            document.addEventListener('keydown', handleEscape);
            return () => {
                document.body.style.overflow = '';
                document.removeEventListener('keydown', handleEscape);
            };
        }
        document.body.style.overflow = '';
    }, [isOpen]);

    const adminOptions = [
        { id: 'users', name: 'Uživatelé', icon: '👥', description: 'Správa uživatelů systému' },
        { id: 'categories', name: 'Kategorie', icon: '🏷️', description: 'Správa kategorií novinek' },
        { id: 'stores', name: 'Prodejny', icon: '🏪', description: 'Správa prodejen' },
        { id: 'tickets', name: 'Tikety', icon: '🐛', description: 'Správa tiketů od prodejců' },
    ];

    const handleOptionClick = (optionId) => {
        navigate(`/${optionId}`);
        setIsOpen(false);
    };

    const handleToggle = () => {
        if (!isOpen) onOpen?.();
        setIsOpen((o) => !o);
    };

    const isCurrentSection = (sectionId) => {
        return location.pathname === `/${sectionId}`;
    };

    const menuContent = (
        <>
            <div className="admin-dropdown-header">
                <span className="admin-title">Administrace</span>
                <span className="admin-subtitle">Správa systému</span>
            </div>
            <div className="admin-options">
                {adminOptions.map((option) => (
                    <button
                        key={option.id}
                        className={`admin-option ${isCurrentSection(option.id) ? 'active' : ''}`}
                        onClick={() => handleOptionClick(option.id)}
                        type="button"
                    >
                        <span className="option-icon">{option.icon}</span>
                        <div className="option-content">
                            <span className="option-name">{option.name}</span>
                            <span className="option-description">{option.description}</span>
                        </div>
                    </button>
                ))}
            </div>
        </>
    );

    const mobileMenuContent = (
        <ul className="mobile-nav-list">
            {adminOptions.map((option) => (
                <li key={option.id}>
                    <button
                        className={`mobile-nav-link ${isCurrentSection(option.id) ? 'active' : ''}`}
                        onClick={() => handleOptionClick(option.id)}
                        type="button"
                    >
                        <span>{option.icon}</span>
                        {option.name}
                    </button>
                </li>
            ))}
        </ul>
    );

    return (
        <div className="admin-dropdown" ref={dropdownRef}>
            <button
                className={`admin-toggle ${isOpen ? 'active' : ''}`}
                onClick={handleToggle}
                title="Administrátorské nastavení"
                type="button"
            >
                ⚙️
            </button>

            {isOpen && (
                <>
                    {createPortal(
                        <div className="admin-mobile-drawer-root" ref={mobileDrawerRef}>
                            <div
                                className={`admin-drawer-backdrop admin-mobile-only ${isOpen ? 'open' : ''}`}
                                onClick={() => setIsOpen(false)}
                                aria-hidden="true"
                            />
                            <div className={`admin-drawer-panel admin-mobile-only ${isOpen ? 'open' : ''}`}>
                                <button
                                    className="mobile-nav-close"
                                    onClick={() => setIsOpen(false)}
                                    aria-label="Zavřít menu"
                                    type="button"
                                >
                                    ×
                                </button>
                                {mobileMenuContent}
                            </div>
                        </div>,
                        document.body
                    )}
                    <div className="admin-dropdown-menu admin-desktop-only">{menuContent}</div>
                </>
            )}
        </div>
    );
};

export default AdminDropdown; 