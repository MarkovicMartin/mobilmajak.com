import React from 'react';
import { PageHeader } from '../../components/ui';
import FinanceFakturyPanel from './FinanceFakturyPanel';

const FinanceFakturyModule = () => (
    <div className="finance-module">
        <PageHeader
            title="Faktury k výdajům"
            subtitle="Přiložte fakturu k výdeji z pokladny nebo platbě"
        />
        <FinanceFakturyPanel intro="Vyberte výdej a nahrajte PDF nebo fotku faktury. Částky DPH můžete doplnit hned, nebo je doplníme později z faktury (OCR)." />
    </div>
);

export default FinanceFakturyModule;
