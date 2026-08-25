import React from 'react';
import { PageHeader } from '../../components/ui';
import FinanceFakturyPanel from './FinanceFakturyPanel';

const FinanceFakturyModule = () => (
    <div className="finance-module">
        <PageHeader
            title="Faktury k výdajům"
            subtitle="Nahrajte FA i bez výdeje, nebo ji přiložte k výběru z pokladny"
        />
        <FinanceFakturyPanel intro="Nejdřív nahrajte PDF nahoře (i před platbou) – spáruje se podle VS. U výdeje s nákupem zboží můžete FA přiložit i přímo k řádku." />
    </div>
);

export default FinanceFakturyModule;
