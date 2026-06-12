import React, { useMemo } from 'react';
import { Tabs, Select } from '../../components/ui';
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
    const tabs = COACHING_SECTIONS.map((section) => ({
        id: section.id,
        label: section.tabLabel,
        icon: section.icon,
        to: section.path ? `/coaching/${section.path}` : '/coaching',
        end: !section.path,
    }));

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
            className="coaching-nav module-tabs--desktop-only"
            legacy
        />
    );
};

export default CoachingNav;
