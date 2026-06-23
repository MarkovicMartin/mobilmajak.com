import React, { useMemo } from 'react';
import { Tabs, Select } from '../../components/ui';
import { MODULE_PAGE_TABS_CLASS, sectionsToUrlTabs } from '../../components/ui/moduleTabs';
import { COACHING_SECTIONS } from './coachingSections';
import './CoachingNav.css';

const CoachingNav = ({
    monthValue,
    monthOptions,
    onMonthChange,
    prodejnaId,
    prodejny,
    onProdejnaChange,
}) => {
    const tabs = sectionsToUrlTabs(COACHING_SECTIONS, {
        pathFor: (section) => (section.path ? `/coaching/${section.path}` : '/coaching'),
        endFor: (section) => !section.path,
    });

    const storeOptions = useMemo(
        () => [
            { value: '', label: 'Vše' },
            ...(prodejny || []).map((p) => ({ value: String(p.id), label: p.nazev })),
        ],
        [prodejny],
    );

    const meta = (
        <div className="coaching-nav-meta">
            {prodejny?.length > 1 && (
                <label className="coaching-nav-filter">
                    <span className="coaching-nav-filter-label">Prodejna</span>
                    <Select
                        options={storeOptions}
                        value={prodejnaId}
                        onChange={onProdejnaChange}
                        aria-label="Filtr prodejny"
                        className="coaching-nav-select"
                    />
                </label>
            )}
            <label className="coaching-nav-filter">
                <span className="coaching-nav-filter-label">Měsíc</span>
                <Select
                    options={monthOptions}
                    value={monthValue}
                    onChange={onMonthChange}
                    aria-label="Filtr měsíce"
                    className="coaching-nav-select"
                />
            </label>
        </div>
    );

    return (
        <Tabs
            tabs={tabs}
            meta={meta}
            accent="pink"
            ariaLabel="Navigace výkonů"
            className={`coaching-nav ${MODULE_PAGE_TABS_CLASS}`}
            legacy={false}
        />
    );
};

export default CoachingNav;
