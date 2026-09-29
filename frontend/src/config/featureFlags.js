/** Build-time přepínače modulů (REACT_APP_* z .env.local / .env.production). */
export const FINANCE_MODULE_ENABLED = process.env.REACT_APP_FINANCE_ENABLED === '1';
/** Denní povinnosti – staging build flag zapíná scripts/frontend-build-vps.sh. Produkce zůstává vypnutá. */
export const DAILY_DUTIES_MODULE_ENABLED = process.env.REACT_APP_DAILY_DUTIES_ENABLED === '1';
