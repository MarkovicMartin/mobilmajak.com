import React from 'react';
import { PageHeader } from '../../components/ui';
import FinanceFakturyPanel from './FinanceFakturyPanel';

const FinanceFakturyModule = () => (
    <div className="finance-module">
        <PageHeader
            title="Faktury k výdajům"
            subtitle="Přiložte fakturu k výdeji z pokladny"
        />
        <FinanceFakturyPanel intro="U výdeje s nákupem zboží stačí přiložit PDF nebo foto – OCR doplní údaje z faktury." />
    </div>
);

export default FinanceFakturyModule;
