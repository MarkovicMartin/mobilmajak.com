/** Build-time přepínače modulů (REACT_APP_* z .env.local / .env.production). */
export const FINANCE_MODULE_ENABLED = process.env.REACT_APP_FINANCE_ENABLED === '1';
