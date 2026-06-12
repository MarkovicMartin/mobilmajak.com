import React, { useState, useEffect, useMemo } from 'react';
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
    const groups = getVisibleNavGroups(auth, { mobile: false });
    const { pathname, state: locationState } = location;

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

    const [expandedMobile, setExpandedMobile] = useState(() => new Set(activeParentKeys));
    const [hoveredParent, setHoveredParent] = useState(null);

    useEffect(() => {
        setExpandedMobile((prev) => {
            const next = new Set(prev);
            activeParentKeys.forEach((k) => next.add(k));
            return next;
        });
    }, [activeParentKeys]);

    const go = (item) => {
        navigateNavItem(navigate, item);
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

    if (mobile) {
        const mobileGroups = getVisibleNavGroups(auth, { mobile: false });
        return (
            <>
                {mobileGroups.map((group) => (
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

    return (
        <>
            {groups.map((group) => (
                <div key={group.id} className={groupClass}>
                    {!collapsed && <span className={groupLabelClass}>{group.label}</span>}
                    {group.items.map((item) => {
                        const hasChildren =
                            PARENTS_WITH_CHILDREN.has(item.sectionKey) && item.children?.length > 0;

                        if (!hasChildren) {
                            return renderLink(item, false);
                        }

                        const isOpen =
                            hoveredParent === item.sectionKey ||
                            activeParentKeys.has(item.sectionKey);

                        return (
                            <div
                                key={item.sectionKey}
                                className={`shell-nav__branch ${isOpen ? 'shell-nav__branch--open' : ''}`}
                                onMouseEnter={() => !collapsed && setHoveredParent(item.sectionKey)}
                                onMouseLeave={() => setHoveredParent(null)}
                            >
                                {renderLink(item, false, collapsed ? () => go(item) : undefined)}
                                {isOpen && !collapsed && (
                                    <div className="shell-nav__children">
                                        {item.children.map((child) => renderLink(child, true))}
                                    </div>
                                )}
                                {isOpen && collapsed && (
                                    <div className="shell-nav__flyout">
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
