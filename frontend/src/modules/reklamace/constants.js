export const REKLAMACE_STATUS = {
    NEZPRACOVANE: 'nezpracovane',
    ODESLANE: 'odeslane',
    VRIZENE: 'vyrizene',
};

export const ZPUSOB_VYRIzeni_OPTIONS = [
    { value: 'vymena', label: 'Výměna' },
    { value: 'dobropis', label: 'Dobropis' },
    { value: 'oprava', label: 'Oprava' },
    { value: 'zamitnuto', label: 'Zamítnuto' },
    { value: 'jine', label: 'Jiné' },
];

export const getRowStatusClass = (item) => {
    if (item.status === REKLAMACE_STATUS.VRIZENE) return 'reklamace-row--vyrizene';
    if (item.status === REKLAMACE_STATUS.ODESLANE) return 'reklamace-row--odeslane';
    if (item.is_overdue) return 'reklamace-row--overdue';
    return 'reklamace-row--nezpracovane';
};

export const getStatusLabel = (item) => {
    if (item.status_label) return item.status_label;
    if (item.status === REKLAMACE_STATUS.VRIZENE) return 'Vyřízené';
    if (item.status === REKLAMACE_STATUS.ODESLANE) return 'Odeslané';
    if (item.is_overdue) return 'Po termínu – odeslat dodavateli';
    return 'Nezpracované';
};
