/** Build-time přepínače modulů (REACT_APP_* z .env.local / .env.production). */
export const FINANCE_MODULE_ENABLED = process.env.REACT_APP_FINANCE_ENABLED === '1';
/** Testovací modul – jen staging/lokál (REACT_APP_DAILY_DUTIES_ENABLED=1). */
export const DAILY_DUTIES_MODULE_ENABLED = process.env.REACT_APP_DAILY_DUTIES_ENABLED === '1';
