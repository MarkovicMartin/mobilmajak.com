import React, { useState, useEffect, useMemo } from 'react';
import {
    getVisibleNavGroups,
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
    profileTaskBadge = 0,
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

    const [expandedInline, setExpandedInline] = useState(() => new Set());
    const [collapsedFlyoutKey, setCollapsedFlyoutKey] = useState(null);

    useEffect(() => {
        setExpandedInline((prev) => {
            if (
                prev.size === activeParentKeys.size
                && [...activeParentKeys].every((k) => prev.has(k))
            ) {
                return prev;
            }
            return new Set(activeParentKeys);
        });
    }, [activeParentKeysKey, activeParentKeys]);

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

    const renderLink = (item, isChild = false, onClickOverride, showLabel = false) => {
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
                title={collapsed && !isChild && !showLabel ? item.label : undefined}
            >
                {renderIcon(item)}
                {(!collapsed || showLabel) && (
                    <span className="shell-nav__label">{item.label}</span>
                )}
                {item.sectionKey === 'my-tasks' && profileTaskBadge > 0 && (!collapsed || showLabel) && (
                    <span className="shell-nav__badge" aria-label={`${profileTaskBadge} upozornění`}>
                        {profileTaskBadge > 99 ? '99+' : profileTaskBadge}
                    </span>
                )}
            </button>
        );
    };

    const toggleInline = (sectionKey) => {
        setExpandedInline((prev) => {
            if (prev.has(sectionKey)) return new Set();
            return new Set([sectionKey]);
        });
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
                            const isOpen = expandedInline.has(item.sectionKey);
                            return (
                                <div key={item.sectionKey} className="shell-nav__branch">
                                    <button
                                        type="button"
                                        className={`${linkClass} shell-nav__branch-toggle ${isOpen ? 'shell-nav__branch-toggle--open' : ''}`}
                                        onClick={() => toggleInline(item.sectionKey)}
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

    const renderDesktopBranch = (item) => {
        const hasChildren =
            PARENTS_WITH_CHILDREN.has(item.sectionKey) && item.children?.length > 0;

        if (!hasChildren) {
            return renderLink(item, false);
        }

        const parentActive = activeParentKeys.has(item.sectionKey);

        if (collapsed) {
            const isOpen = collapsedFlyoutKey === item.sectionKey;
            return (
                <div
                    key={item.sectionKey}
                    className={[
                        'shell-nav__branch',
                        'shell-nav__branch--collapsed',
                        parentActive ? 'shell-nav__branch--active' : '',
                    ].filter(Boolean).join(' ')}
                    onMouseEnter={() => setCollapsedFlyoutKey(item.sectionKey)}
                    onMouseLeave={() => setCollapsedFlyoutKey((current) => (
                        current === item.sectionKey ? null : current
                    ))}
                >
                    <button
                        type="button"
                        className={`${linkClass} shell-nav__branch-toggle ${parentActive ? activeClass : ''}`.trim()}
                        aria-haspopup="true"
                        title={item.label}
                        tabIndex={0}
                    >
                        {renderIcon(item)}
                    </button>
                    {isOpen && (
                        <div className="shell-nav__flyout" role="menu">
                            <div className="shell-nav__flyout-panel">
                                <div className="shell-nav__flyout-title">{item.label}</div>
                                {item.children.map((child) =>
                                    renderLink(
                                        child,
                                        true,
                                        () => {
                                            go(child);
                                            setCollapsedFlyoutKey(null);
                                        },
                                        true,
                                    ),
                                )}
                            </div>
                        </div>
                    )}
                </div>
            );
        }

        const isOpen = expandedInline.has(item.sectionKey);
        return (
            <div
                key={item.sectionKey}
                className={[
                    'shell-nav__branch',
                    parentActive ? 'shell-nav__branch--active' : '',
                ].filter(Boolean).join(' ')}
            >
                <button
                    type="button"
                    className={`${linkClass} shell-nav__branch-toggle ${isOpen ? 'shell-nav__branch-toggle--open' : ''} ${parentActive ? activeClass : ''}`.trim()}
                    onClick={() => toggleInline(item.sectionKey)}
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
    };

    return (
        <>
            {groups.map((group) => (
                <div key={group.id} className={groupClass}>
                    {!collapsed && <span className={groupLabelClass}>{group.label}</span>}
                    {group.items.map((item) => renderDesktopBranch(item))}
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
    collapsed = false,
    onNavigate,
}) => {
    const profileActive = location.pathname === '/profile';

    const goProfile = () => {
        navigate('/profile');
        onNavigate?.();
    };

    return (
        <button
            type="button"
            className={`${linkClass} ${profileActive ? activeClass : ''}`.trim()}
            onClick={goProfile}
            aria-current={profileActive ? 'page' : undefined}
            title={collapsed ? 'Můj profil' : undefined}
        >
            <i className="fas fa-user" aria-hidden="true" />
            {!collapsed && <span className="shell-nav__label">Můj profil</span>}
        </button>
    );
};

export default ShellNavLinks;
