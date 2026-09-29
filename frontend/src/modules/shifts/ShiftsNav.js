import React, { useMemo } from 'react';
import { Tabs } from '../../components/ui';
import { MODULE_PAGE_TABS_CLASS, sectionsToStateTabs } from '../../components/ui/moduleTabs';
import { SHIFTS_SECTIONS } from './shiftsSections';

const ShiftsNav = ({ activeView, onViewChange, isAdmin, canManageShifts }) => {
    const tabs = useMemo(() => {
        const visible = SHIFTS_SECTIONS.filter((s) => {
            if (s.adminOnly && !isAdmin) return false;
            if (s.manageOnly && !canManageShifts) return false;
            return true;
        });
        return sectionsToStateTabs(visible);
    }, [isAdmin, canManageShifts]);

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
