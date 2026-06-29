/** Filtry sdílené mezi oběma panely (kanál, prodejna). */
export const POLOZKY_SCOPE_KEYS = ['kanal', 'prodejna_id'];

export const pickPolozkyScope = (filters) => ({
    kanal: filters.kanal ?? 'all',
    prodejna_id: filters.prodejna_id ?? '',
});

export const mergePolozkyScope = (filters, scope) => {
    if (!scope) return filters;
    return {
        ...filters,
        ...scope,
        segment: 'vse',
        seller_mode: 'all',
        user_ids: '',
    };
};

export const buildInitialPolozkyFilters = () => {
    const now = new Date();
    return {
        period: 'monthly_select',
        start_date: '',
        end_date: '',
        selected_month: `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`,
        kanal: 'all',
        prodejna_id: '',
        segment: 'vse',
        kategorie: '',
    };
};
