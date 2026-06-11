import React from 'react';
import ModuleSubnav from '../../components/ModuleSubnav';
import { PLANS_SECTIONS } from './plansSections';
import './PlansNav.css';

const PlansNav = ({
  viewMode,
  onSwitch,
  showMonth,
  monthValue,
  monthOptions,
  monthLabels,
  onMonthChange,
  showPlanRezim,
  planovaciRezim,
  onPlanovaciRezimChange,
}) => {
  const tabs = PLANS_SECTIONS.map((section) => ({
    id: section.id,
    label: section.tabLabel,
    icon: section.icon,
  }));

  const meta = (
    <>
      {showPlanRezim && (
        <div className="plans-nav-rezim" role="group" aria-label="Režim plánování">
          <button
            type="button"
            className={`plans-nav-rezim-btn${planovaciRezim === 'top_down' ? ' plans-nav-rezim-btn--active' : ''}`}
            onClick={() => onPlanovaciRezimChange('top_down')}
            title="Celková částka a rozpočet na prodejny"
          >
            Top-down
          </button>
          <button
            type="button"
            className={`plans-nav-rezim-btn${planovaciRezim === 'bottom_up' ? ' plans-nav-rezim-btn--active' : ''}`}
            onClick={() => onPlanovaciRezimChange('bottom_up')}
            title="Kč cíle prodejen, celek se sečte"
          >
            Bottom-up
          </button>
        </div>
      )}
      {showMonth && (
        <label className="plans-nav-month">
          <span className="plans-nav-month-label">Měsíc</span>
          <select
            className="plans-nav-month-select"
            value={monthValue}
            onChange={(e) => onMonthChange(e.target.value)}
            aria-label="Vybraný měsíc"
          >
            {monthOptions.map((o) => (
              <option key={`${o.rok}-${o.mesic}`} value={`${o.rok}-${o.mesic}`}>
                {monthLabels[o.mesic - 1]} {o.rok}
              </option>
            ))}
          </select>
        </label>
      )}
    </>
  );

  return (
    <ModuleSubnav
      tabs={tabs}
      activeId={viewMode}
      onTabChange={onSwitch}
      meta={meta}
      accent="blue"
      ariaLabel="Sekce plánů"
      className="plans-nav"
    />
  );
};

export default PlansNav;
