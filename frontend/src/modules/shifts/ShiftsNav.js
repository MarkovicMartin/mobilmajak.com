import React, { useMemo } from 'react';
import { Tabs } from '../../components/ui';
import { MODULE_PAGE_TABS_CLASS, sectionsToStateTabs } from '../../components/ui/moduleTabs';
import { SHIFTS_SECTIONS } from './shiftsSections';

const ShiftsNav = ({ activeView, onViewChange, isAdmin }) => {
    const tabs = useMemo(() => {
        const visible = SHIFTS_SECTIONS.filter((s) => !s.adminOnly || isAdmin);
        return sectionsToStateTabs(visible);
    }, [isAdmin]);

    return (
        <Tabs
            tabs={tabs}
            activeId={activeView}
            onTabChange={onViewChange}
            accent="pink"
            ariaLabel="Sekce směn"
            className={`shifts-nav ${MODULE_PAGE_TABS_CLASS}`}
            legacy={false}
        />
    );
};

export default ShiftsNav;
