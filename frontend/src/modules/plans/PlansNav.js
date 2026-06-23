import React, { useMemo } from 'react';
import { Tabs, Select, SegmentControl } from '../../components/ui';
import { MODULE_PAGE_TABS_CLASS, sectionsToUrlTabs } from '../../components/ui/moduleTabs';
import { PLANS_SECTIONS } from './plansSections';
import './PlansNav.css';

const REZIM_OPTIONS = [
  { id: 'top_down', label: 'Top-down', title: 'Celková částka a rozpočet na prodejny' },
  { id: 'bottom_up', label: 'Bottom-up', title: 'Kč cíle prodejen, celek se sečte' },
];

const PlansNav = ({
  showMonth,
  monthValue,
  monthOptions,
  monthLabels,
  onMonthChange,
  showPlanRezim,
  planovaciRezim,
  onPlanovaciRezimChange,
  vyhledFilters,
}) => {
  const tabs = sectionsToUrlTabs(PLANS_SECTIONS, {
    pathFor: (section) => `/plans/${section.path}`,
    endFor: (section) => section.path === 'vyhled',
  });

  const monthSelectOptions = useMemo(
    () => monthOptions.map((o) => ({
      value: `${o.rok}-${o.mesic}`,
      label: `${monthLabels[o.mesic - 1]} ${o.rok}`,
    })),
    [monthOptions, monthLabels],
  );

  const meta = (
    <>
      {vyhledFilters}
      {showPlanRezim && (
        <SegmentControl
          options={REZIM_OPTIONS}
          value={planovaciRezim}
          onChange={onPlanovaciRezimChange}
          ariaLabel="Režim plánování"
          className="plans-nav-rezim-segment"
        />
      )}
      {showMonth && (
        <label className="plans-nav-month">
          <span className="plans-nav-month-label">Měsíc</span>
          <Select
            options={monthSelectOptions}
            value={monthValue}
            onChange={onMonthChange}
            aria-label="Vybraný měsíc"
            className="plans-nav-month-select"
          />
        </label>
      )}
    </>
  );

  return (
    <Tabs
      tabs={tabs}
      meta={meta}
      accent="blue"
      ariaLabel="Sekce plánů"
      className={`plans-nav ${MODULE_PAGE_TABS_CLASS}`}
      legacy={false}
    />
  );
};

export default PlansNav;
