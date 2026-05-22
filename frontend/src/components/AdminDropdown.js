import React, { useState, useRef, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { useNavigate, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ADMIN_SECTIONS, getAdminSectionFromPath } from './adminSections';
import './AdminDropdown.css';

const springHover = { type: 'spring', stiffness: 300, damping: 22 };

const AdminDropdown = ({ onOpen }) => {
    const [isOpen, setIsOpen] = useState(false);
    const dropdownRef = useRef(null);
    const mobileDrawerRef = useRef(null);
    const navigate = useNavigate();
    const location = useLocation();

    const activeSection = getAdminSectionFromPath(location.pathname);
    const showExpandedLabel = !!activeSection;
    const expandedLabel = activeSection?.name ?? 'Nastavení';

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

    const handleOptionClick = (optionId) => {
        navigate(`/${optionId}`);
        setIsOpen(false);
    };

    const handleToggle = () => {
        if (!isOpen) onOpen?.();
        setIsOpen((o) => !o);
    };

    const isCurrentSection = (sectionId) => location.pathname === `/${sectionId}`;

    const menuContent = (
        <>
            <div className="admin-dropdown-header">
                <span className="admin-title">Administrace</span>
                <span className="admin-subtitle">Správa systému</span>
            </div>
            <div className="admin-options">
                {ADMIN_SECTIONS.map((option) => (
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
            {ADMIN_SECTIONS.map((option) => (
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
            <motion.div
                className={`dock-nav-item-wrap ${showExpandedLabel ? 'dock-nav-item-wrap--expanded' : ''}`}
                whileHover={showExpandedLabel ? { scale: 1.04 } : { scale: 1.08 }}
                transition={springHover}
            >
                <motion.button
                    type="button"
                    layout
                    className={`dock-icon-btn admin-toggle-dock ${isOpen ? 'admin-toggle-dock--open' : ''} ${showExpandedLabel ? 'dock-icon-btn--active dock-icon-btn--with-label' : ''}`}
                    onClick={handleToggle}
                    data-tooltip={showExpandedLabel ? undefined : 'Nastavení'}
                    title={expandedLabel}
                    transition={springHover}
                    aria-expanded={isOpen}
                >
                    <i className="fas fa-cog" />
                    {showExpandedLabel && (
                        <motion.span
                            className="dock-nav-label"
                            initial={{ opacity: 0, maxWidth: 0 }}
                            animate={{ opacity: 1, maxWidth: 160 }}
                            transition={{ duration: 0.22, ease: 'easeOut' }}
                        >
                            {expandedLabel}
                        </motion.span>
                    )}
                    {showExpandedLabel && (
                        <motion.span
                            layoutId="dock-active-dot-admin"
                            className="dock-active-dot"
                            transition={springHover}
                        />
                    )}
                </motion.button>
            </motion.div>

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
