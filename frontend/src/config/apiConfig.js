/**
 * Konfigurace API endpointů pro analytika
 * 
 * Tato konfigurace umožňuje snadné přepínání mezi:
 * - Starými Google Sheets endpointy (deprecated)
 * - Apify endpointy (deprecated)
 * - Novými WEB_PRODEJE endpointy (nejnovější - přímo z prodejní tabulky)
 */

// Nastavení zdroje dat
const DATA_SOURCE = {
    GOOGLE_SHEETS: 'google_sheets',  // DEPRECATED
    APIFY: 'apify',                  // DEPRECATED
    WEB_PRODEJE: 'web_prodeje'       // NEJNOVĚJŠÍ - PŘÍMO Z PRODEJNÍ TABULKY
};

// Výchozí zdroj dat - ZMĚNIT NA 'web_prodeje' PRO POUŽÍVÁNÍ NEJNOVĚJŠÍCH DAT
const CURRENT_DATA_SOURCE = DATA_SOURCE.WEB_PRODEJE;

// Konfigurace endpointů
const API_ENDPOINTS = {
    [DATA_SOURCE.GOOGLE_SHEETS]: {
        // Staré Google Sheets endpointy (DEPRECATED)
        data: '/api/analytics/prodejny-data/',
        dataByDate: '/api/analytics/prodejny-data/by-date/',
        save: '/api/analytics/prodejny-data/save/',
        debug: '/api/analytics/prodejny-data/debug/',
        salespersonToday: '/api/analytics/salesperson/today/',
        salespersonMonthly: '/api/analytics/salesperson/monthly/',
        salespersonPointsToday: '/api/analytics/salesperson/points/today/',
        salespersonPointsMonthly: '/api/analytics/salesperson/points/monthly/',
        leaderboardPoints: '/api/analytics/leaderboard/points/',
        leaderboardAverageItems: '/api/analytics/leaderboard/average-items/',
        chartsData: '/api/analytics/charts-data/',
        backupInfo: '/api/analytics/backup-info/',
        name: 'Google Sheets (deprecated)',
        description: 'Stará implementace s Google Sheets - již se nepoužívá'
    },
    [DATA_SOURCE.APIFY]: {
        // Apify endpointy (DEPRECATED)
        data: '/api/analytics/apify/data/',
        dataByDate: '/api/analytics/apify/data/by-date/',
        save: null, // Apify ukládá automaticky, není potřeba save endpoint
        debug: null, // Debug endpoint není potřeba pro Apify
        salespersonToday: '/api/analytics/apify/salesperson/today/',
        salespersonMonthly: '/api/analytics/apify/salesperson/monthly/',
        salespersonPointsToday: '/api/analytics/apify/salesperson/points/today/',
        salespersonPointsMonthly: '/api/analytics/apify/salesperson/points/monthly/',
        leaderboardPoints: '/api/analytics/apify/leaderboard/points/',
        leaderboardAverageItems: '/api/analytics/apify/leaderboard/average-items/',
        chartsData: '/api/analytics/web-prodeje-charts-data/',
        backupInfo: '/api/analytics/apify/backup-info/',
        name: 'Apify tabulky (deprecated)',
        description: 'Implementace s Apify tabulkami - již se nepoužívá'
    },
    [DATA_SOURCE.WEB_PRODEJE]: {
        // Nové WEB_PRODEJE endpointy (NEJNOVĚJŠÍ)
        data: '/api/analytics/web-prodeje/polozky/',
        dataByDate: '/api/analytics/web-prodeje/polozky/', // Používá parametr date
        save: null, // Data se čtou přímo z prodejní tabulky
        debug: null, // Debug není potřeba
        // Můj profil – přímo z WEB_PRODEJE_ALL
        salespersonToday: '/api/analytics/web-prodeje/salesperson/today/',
        salespersonMonthly: '/api/analytics/web-prodeje/salesperson/monthly/',
        salespersonPointsToday: '/api/analytics/web-prodeje/salesperson/points/today/',
        salespersonPointsMonthly: '/api/analytics/web-prodeje/salesperson/points/monthly/',
        salespersonActiveDates: '/api/analytics/web-prodeje/salesperson/active-dates/',
        leaderboardPoints: '/api/analytics/web-prodeje/leaderboard/points/',
        leaderboardPointsToday: '/api/analytics/web-prodeje/leaderboard/points/today/',
        leaderboardAverageItems: '/api/analytics/web-prodeje/leaderboard/average-items/',
        chartsData: '/api/analytics/web-prodeje-charts-data/',
        backupInfo: '/api/analytics/backup-info/', // Backup info endpoint
        name: 'WEB_PRODEJE (nejnovější)',
        description: 'Nejnovější implementace čtoucí přímo z tabulky WEB_PRODEJE'
    }
};

// Exportované funkce pro používání v komponentách
export const getApiEndpoints = () => {
    return {
        ...API_ENDPOINTS[CURRENT_DATA_SOURCE],
        // Pro pohodlné použití v komponentách
        webProdejePolozky: API_ENDPOINTS[CURRENT_DATA_SOURCE].data,
        chartsData: API_ENDPOINTS[CURRENT_DATA_SOURCE].chartsData,
    };
};

export const getCurrentDataSource = () => {
    return CURRENT_DATA_SOURCE;
};

export const getDataSourceName = () => {
    return API_ENDPOINTS[CURRENT_DATA_SOURCE].name;
};

export const getDataSourceDescription = () => {
    return API_ENDPOINTS[CURRENT_DATA_SOURCE].description;
};

export const isApifyEnabled = () => {
    return CURRENT_DATA_SOURCE === DATA_SOURCE.APIFY;
};

export const isGoogleSheetsEnabled = () => {
    return CURRENT_DATA_SOURCE === DATA_SOURCE.GOOGLE_SHEETS;
};

// Helper funkce pro kontrolu dostupnosti endpointu
export const isEndpointAvailable = (endpointName) => {
    const endpoints = getApiEndpoints();
    return endpoints[endpointName] !== null && endpoints[endpointName] !== undefined;
};

// Výchozí export
export default {
    getApiEndpoints,
    getCurrentDataSource,
    getDataSourceName,
    getDataSourceDescription,
    isApifyEnabled,
    isGoogleSheetsEnabled,
    isEndpointAvailable,
    DATA_SOURCE
}; 