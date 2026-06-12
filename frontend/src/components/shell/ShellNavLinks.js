import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { createPortal } from 'react-dom';
import {
    getVisibleNavGroups,
    getProfileNavChildren,
    isNavItemLinkActive,
    navigateNavItem,
} from '../../config/navigation';
import { PARENTS_WITH_CHILDREN } from '../../config/navChildren';

const ShellNavLinks = ({
    auth,
    location,
    navigate,
    linkClass,
    activeClass,
    childClass,
    groupClass,
    groupLabelClass,
    mobile = false,
    collapsed = false,
    onNavigate,
}) => {
    const { pathname, state: locationState } = location;
    const isAdminUser = auth.isAdmin();
    const canTasks = auth.canManageTasks();
    const canCoaching = auth.canAccessCoaching();

    const groups = useMemo(() => {
        const stableAuth = {
            isAdmin: () => isAdminUser,
            canManageTasks: () => canTasks,
            canAccessCoaching: () => canCoaching,
        };
        return getVisibleNavGroups(stableAuth, { mobile: false });
    }, [isAdminUser, canTasks, canCoaching]);

    const activeParentKeys = useMemo(() => {
        const keys = new Set();
        groups.forEach((group) => {
            group.items.forEach((item) => {
                if (!item.children?.length) return;
                const parentActive = isNavItemLinkActive(item, pathname, locationState);
                const childActive = item.children.some((c) =>
                    isNavItemLinkActive(c, pathname, locationState),
                );
                if (parentActive || childActive) keys.add(item.sectionKey);
            });
        });
        return keys;
    }, [groups, pathname, locationState]);

    const activeParentKeysKey = useMemo(
        () => [...activeParentKeys].sort().join('|'),
        [activeParentKeys],
    );

    const [expandedMobile, setExpandedMobile] = useState(() => new Set());
    const [openFlyout, setOpenFlyout] = useState(null);
    const [flyoutRect, setFlyoutRect] = useState(null);

    useEffect(() => {
        setExpandedMobile((prev) => {
            let changed = false;
            const next = new Set(prev);
            activeParentKeys.forEach((k) => {
                if (!next.has(k)) {
                    next.add(k);
                    changed = true;
                }
            });
            return changed ? next : prev;
        });
    }, [activeParentKeysKey, activeParentKeys]);

    const openFlyoutItem = useMemo(
        () => groups.flatMap((g) => g.items).find((i) => i.sectionKey === openFlyout),
        [groups, openFlyout],
    );

    const updateFlyoutRect = useCallback((buttonEl) => {
        if (!buttonEl) return;
        const rect = buttonEl.getBoundingClientRect();
        setFlyoutRect({
            top: rect.top,
            left: rect.right + 8,
        });
    }, []);

    useEffect(() => {
        setOpenFlyout(null);
        setFlyoutRect(null);
    }, [pathname]);

    useEffect(() => {
        if (!openFlyout) return undefined;
        const onReposition = () => {
            const btn = document.querySelector(
                `.shell-nav__branch-toggle[aria-expanded="true"]`,
            );
            if (btn) updateFlyoutRect(btn);
        };
        window.addEventListener('resize', onReposition);
        window.addEventListener('scroll', onReposition, true);
        return () => {
            window.removeEventListener('resize', onReposition);
            window.removeEventListener('scroll', onReposition, true);
        };
    }, [openFlyout, updateFlyoutRect]);

    useEffect(() => {
        if (!openFlyout) return undefined;
        const closeOnOutside = (e) => {
            if (e.target.closest('.shell-nav__branch--flyout-open')) return;
            if (e.target.closest('.shell-nav__flyout--fixed')) return;
            setOpenFlyout(null);
            setFlyoutRect(null);
        };
        const closeOnEscape = (e) => {
            if (e.key === 'Escape') closeFlyout();
        };
        document.addEventListener('mousedown', closeOnOutside);
        document.addEventListener('keydown', closeOnEscape);
        return () => {
            document.removeEventListener('mousedown', closeOnOutside);
            document.removeEventListener('keydown', closeOnEscape);
        };
    }, [openFlyout]);

    const closeFlyout = () => {
        setOpenFlyout(null);
        setFlyoutRect(null);
    };

    const go = (item) => {
        navigateNavItem(navigate, item);
        closeFlyout();
        onNavigate?.();
    };

    const renderIcon = (item) => {
        const icon = item.icon || 'fa-circle';
        if (icon.startsWith('fa-')) {
            return <i className={`fas ${icon}`} aria-hidden="true" />;
        }
        return <span className="shell-nav__emoji" aria-hidden="true">{icon}</span>;
    };

    const renderLink = (item, isChild = false, onClickOverride) => {
        const active = isNavItemLinkActive(item, pathname, locationState);
        const cls = [
            linkClass,
            active ? activeClass : '',
            isChild ? childClass : '',
        ]
            .filter(Boolean)
            .join(' ');

        return (
            <button
                key={item.sectionKey}
                type="button"
                className={cls}
                onClick={onClickOverride || (() => go(item))}
                aria-current={active ? 'page' : undefined}
                title={collapsed && !isChild ? item.label : undefined}
            >
                {renderIcon(item)}
                {!collapsed && <span className="shell-nav__label">{item.label}</span>}
            </button>
        );
    };

    const toggleMobile = (sectionKey) => {
        setExpandedMobile((prev) => {
            const next = new Set(prev);
            if (next.has(sectionKey)) next.delete(sectionKey);
            else next.add(sectionKey);
            return next;
        });
    };

    const toggleFlyout = (sectionKey, buttonEl) => {
        if (openFlyout === sectionKey) {
            closeFlyout();
            return;
        }
        updateFlyoutRect(buttonEl);
        setOpenFlyout(sectionKey);
    };

    if (mobile) {
        return (
            <>
                {groups.map((group) => (
                    <div key={group.id} className={groupClass}>
                        <span className={groupLabelClass}>{group.label}</span>
                        {group.items.map((item) => {
                            const hasChildren = item.children?.length > 0;
                            if (!hasChildren) {
                                return renderLink(item, false);
                            }
                            const isOpen = expandedMobile.has(item.sectionKey);
                            return (
                                <div key={item.sectionKey} className="shell-nav__branch">
                                    <button
                                        type="button"
                                        className={`${linkClass} shell-nav__branch-toggle ${isOpen ? 'shell-nav__branch-toggle--open' : ''}`}
                                        onClick={() => toggleMobile(item.sectionKey)}
                                        aria-expanded={isOpen}
                                    >
                                        {renderIcon(item)}
                                        <span className="shell-nav__label">{item.label}</span>
                                        <i className={`fas fa-chevron-${isOpen ? 'up' : 'down'} shell-nav__chevron`} aria-hidden="true" />
                                    </button>
                                    {isOpen && (
                                        <div className="shell-nav__children">
                                            {item.children.map((child) => renderLink(child, true))}
                                        </div>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                ))}
            </>
        );
    }

    const flyoutPortal = openFlyoutItem && flyoutRect && createPortal(
        <div
            className="shell-nav__flyout shell-nav__flyout--fixed"
            role="menu"
            style={{ top: flyoutRect.top, left: flyoutRect.left }}
        >
            <div className="shell-nav__flyout-title">{openFlyoutItem.label}</div>
            {openFlyoutItem.children.map((child) => renderLink(child, true))}
        </div>,
        document.body,
    );

    return (
        <>
            {flyoutPortal}
            {groups.map((group) => (
                <div key={group.id} className={groupClass}>
                    {!collapsed && <span className={groupLabelClass}>{group.label}</span>}
                    {group.items.map((item) => {
                        const hasChildren =
                            PARENTS_WITH_CHILDREN.has(item.sectionKey) && item.children?.length > 0;

                        if (!hasChildren) {
                            return renderLink(item, false);
                        }

                        const isFlyoutOpen = openFlyout === item.sectionKey;
                        const parentActive = activeParentKeys.has(item.sectionKey);

                        return (
                            <div
                                key={item.sectionKey}
                                className={[
                                    'shell-nav__branch',
                                    isFlyoutOpen ? 'shell-nav__branch--flyout-open' : '',
                                    parentActive ? 'shell-nav__branch--active' : '',
                                ].filter(Boolean).join(' ')}
                            >
                                <button
                                    type="button"
                                    className={`${linkClass} shell-nav__branch-toggle ${isFlyoutOpen ? 'shell-nav__branch-toggle--open' : ''} ${parentActive ? activeClass : ''}`.trim()}
                                    onClick={(e) => toggleFlyout(item.sectionKey, e.currentTarget)}
                                    aria-expanded={isFlyoutOpen}
                                    aria-haspopup="true"
                                    title={collapsed ? item.label : undefined}
                                >
                                    {renderIcon(item)}
                                    {!collapsed && <span className="shell-nav__label">{item.label}</span>}
                                    {!collapsed && (
                                        <i className={`fas fa-chevron-${isFlyoutOpen ? 'up' : 'down'} shell-nav__chevron`} aria-hidden="true" />
                                    )}
                                </button>
                            </div>
                        );
                    })}
                </div>
            ))}
        </>
    );
};

export const ShellProfileLinks = ({
    location,
    navigate,
    linkClass,
    activeClass,
    childClass,
    collapsed = false,
    mobile = false,
    profileTaskBadge = 0,
    onNavigate,
}) => {
    const children = getProfileNavChildren({
        isAdmin: () => true,
        canManageTasks: () => true,
        canAccessCoaching: () => true,
    });
    const { pathname, state: locationState } = location;
    const [profileOpen, setProfileOpen] = useState(pathname === '/profile');

    useEffect(() => {
        if (pathname === '/profile') setProfileOpen(true);
    }, [pathname]);

    if (mobile) {
        return (
            <>
                <button
                    type="button"
                    className={`${linkClass} shell-nav__branch-toggle ${profileOpen ? 'shell-nav__branch-toggle--open' : ''}`}
                    onClick={() => setProfileOpen((v) => !v)}
                    aria-expanded={profileOpen}
                >
                    <i className="fas fa-user" aria-hidden="true" />
                    Můj profil
                    {profileTaskBadge > 0 && (
                        <span className="badge">{profileTaskBadge > 99 ? '99+' : profileTaskBadge}</span>
                    )}
                    <i className={`fas fa-chevron-${profileOpen ? 'up' : 'down'} shell-nav__chevron`} aria-hidden="true" />
                </button>
                {profileOpen &&
                    children.map((item) => {
                        const active = isNavItemLinkActive(item, pathname, locationState);
                        return (
                            <button
                                key={item.sectionKey}
                                type="button"
                                className={`${linkClass} ${active ? activeClass : ''} ${childClass}`.trim()}
                                onClick={() => {
                                    navigateNavItem(navigate, item);
                                    onNavigate?.();
                                }}
                            >
                                <i className={`fas ${item.icon}`} aria-hidden="true" />
                                {item.label}
                            </button>
                        );
                    })}
            </>
        );
    }

    const profileActive = pathname === '/profile';
    return (
        <button
            type="button"
            className={`${linkClass} ${profileActive ? activeClass : ''}`.trim()}
            onClick={() => {
                navigate('/profile');
                onNavigate?.();
            }}
            title={collapsed ? 'Můj profil' : undefined}
        >
            <i className="fas fa-user" aria-hidden="true" />
            {!collapsed && <span className="shell-nav__label">Můj profil</span>}
        </button>
    );
};

export default ShellNavLinks;
