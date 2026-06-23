import React, { useMemo } from 'react';
import { useAuth } from '../../context/AuthContext';
import { Tabs } from '../../components/ui';
import { MODULE_PAGE_TABS_CLASS, sectionsToUrlTabs } from '../../components/ui/moduleTabs';
import { getVisibleTasksSections } from './tasksSections';

const TasksNav = () => {
    const { isAdmin, canManageTasks } = useAuth();

    const tabs = useMemo(() => {
        const visible = getVisibleTasksSections({ isAdmin, canManageTasks });
        return sectionsToUrlTabs(visible, {
            pathFor: (section) => `/tasks/${section.path}`,
            endFor: (section) => section.path === 'mine',
        });
    }, [isAdmin, canManageTasks]);

    if (tabs.length <= 1) return null;

    return (
        <Tabs
            tabs={tabs}
            ariaLabel="Sekce úkolů"
            className={`tasks-nav ${MODULE_PAGE_TABS_CLASS}`}
            legacy={false}
        />
    );
};

export default TasksNav;
