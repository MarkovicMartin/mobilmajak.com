import React from 'react';
import { PageHeader } from '../../components/ui';
import FinanceFakturyPanel from './FinanceFakturyPanel';

const FinanceFakturyModule = () => (
    <div className="finance-module">
        <PageHeader
            title="Faktury k výdajům"
            subtitle="Přiložte fakturu k výdeji z pokladny"
        />
        <FinanceFakturyPanel intro="Vyberte výdej z pokladny vaší prodejny a nahrajte PDF nebo fotku faktury. Platby z bankovního účtu (Fio) řeší administrátor." />
    </div>
);

export default FinanceFakturyModule;
