import React from 'react';
import ModuleSubnav from '../../components/ModuleSubnav';
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

    const meta = (
        <>
            {prodejny?.length > 1 && (
                <label className="coaching-nav-filter">
                    <span className="coaching-nav-filter-label">Prodejna</span>
                    <select
                        className="coaching-nav-select"
                        value={prodejnaId}
                        onChange={(e) => onProdejnaChange(e.target.value)}
                    >
                        <option value="">Vše</option>
                        {prodejny.map((p) => (
                            <option key={p.id} value={p.id}>{p.nazev}</option>
                        ))}
                    </select>
                </label>
            )}
            <label className="coaching-nav-filter">
                <span className="coaching-nav-filter-label">Měsíc</span>
                <select
                    className="coaching-nav-select"
                    value={monthValue}
                    onChange={(e) => onMonthChange(e.target.value)}
                >
                    {monthOptions.map((opt) => (
                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                </select>
            </label>
        </>
    );

    return (
        <ModuleSubnav
            tabs={tabs}
            meta={meta}
            accent="pink"
            ariaLabel="Navigace výkonů"
            className="coaching-nav"
        />
    );
};

export default CoachingNav;
