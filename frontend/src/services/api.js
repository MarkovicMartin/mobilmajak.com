import axios from 'axios';

// Základní konfigurace axios - použijeme relativní cestu pro stejnou doménu
const API_BASE_URL = '/api';

const api = axios.create({
    baseURL: API_BASE_URL,
    withCredentials: true, // Pro session cookies
    headers: {
        'Content-Type': 'application/json',
    },
});

// Interceptor pro přidání CSRF tokenu
api.interceptors.request.use((config) => {
    // Pro login endpoint nepřidáváme CSRF token
    if (config.url === '/users/login/') {
        return config;
    }
    
    // Získání CSRF tokenu z cookies
    const csrfToken = document.cookie
        .split('; ')
        .find(row => row.startsWith('csrftoken='))
        ?.split('=')[1];
    
    if (csrfToken) {
        config.headers['X-CSRFToken'] = csrfToken;
    }
    
    return config;
});

api.interceptors.response.use(
    (response) => response,
    (error) => {
        import('../utils/uxFrictionMonitor').then(({ reportApiUxError }) => {
            reportApiUxError(error);
        });
        return Promise.reject(error);
    }
);



// API funkce pro uživatele
export const userAPI = {
    // Přihlášení
    login: async (username, password) => {
        // Pro login nepoužíváme CSRF token
        const response = await api.post('/users/login/', {
            uzivatelske_jmeno: username,
            heslo: password,
        });
        return response.data;
    },

    // Odhlášení
    logout: async () => {
        const response = await api.post('/users/logout/');
        return response.data;
    },

    // Získání aktuálního uživatele
    getCurrentUser: async () => {
        const response = await api.get('/users/current/');
        return response.data;
    },

    // Seznam uživatelů (ADMIN + VEDOUCI); výchozí jen aktivní
    getUsers: async ({ aktivni = true } = {}) => {
        const params = {};
        if (aktivni === true) params.aktivni = 'true';
        else if (aktivni === false) params.aktivni = 'false';
        else if (aktivni === 'all') params.aktivni = 'all';
        const response = await api.get('/users/list/', { params });
        return response.data;
    },

    // Vytvoření nového uživatele (pouze pro adminy)
    createUser: async (userData) => {
        const response = await api.post('/users/create/', userData);
        return response.data;
    },

    // Aktualizace uživatele (pouze pro adminy)
    updateUser: async (userId, userData) => {
        const response = await api.put(`/users/update/${userId}/`, userData);
        return response.data;
    },

    // Smazání uživatele (pouze pro adminy)
    deleteUser: async (userId) => {
        const response = await api.delete(`/users/delete/${userId}/`);
        return response.data;
    },
};

// API funkce pro prodejny
export const storeAPI = {
    // Seznam všech prodejen
    getStores: async (params = {}) => {
        const queryParams = new URLSearchParams();
        if (params.aktivni !== undefined) queryParams.append('aktivni', params.aktivni);
        if (params.search) queryParams.append('search', params.search);
        
        const response = await api.get(`/stores/prodejny/?${queryParams}`);
        return response.data;
    },

    // Detail jedné prodejny
    getStore: async (storeId) => {
        const response = await api.get(`/stores/prodejny/${storeId}/`);
        return response.data;
    },

    // Vytvoření nové prodejny
    createStore: async (storeData) => {
        const response = await api.post('/stores/prodejny/', storeData);
        return response.data;
    },

    // Aktualizace prodejny
    updateStore: async (storeId, storeData) => {
        const response = await api.put(`/stores/prodejny/${storeId}/`, storeData);
        return response.data;
    },

    // Smazání prodejny
    deleteStore: async (storeId) => {
        const response = await api.delete(`/stores/prodejny/${storeId}/`);
        return response.data;
    },

    // Seznam prodejen pro dropdown/choice
    getStoreChoices: async () => {
        const response = await api.get('/stores/prodejny/choices/');
        return response.data;
    },

    // Hromadná změna statusu prodejen
    bulkUpdateStatus: async (storeIds, aktivni) => {
        const response = await api.post('/stores/prodejny/bulk_update_status/', {
            store_ids: storeIds,
            aktivni: aktivni
        });
        return response.data;
    },
};

// API funkce pro kategorie
export const categoryAPI = {
    // Seznam všech kategorií
    getCategories: async () => {
        const response = await api.get('/news/kategorie/');
        return response.data;
    },

    // Vytvoření nové kategorie
    createCategory: async (categoryData) => {
        const response = await api.post('/news/kategorie/vytvorit/', categoryData);
        return response.data;
    },

    // Aktualizace kategorie
    updateCategory: async (categoryId, categoryData) => {
        const response = await api.put(`/news/kategorie/${categoryId}/`, categoryData);
        return response.data;
    },

    // Smazání kategorie
    deleteCategory: async (categoryId) => {
        const response = await api.delete(`/news/kategorie/${categoryId}/`);
        return response.data;
    },
};

// API funkce pro tikety
export const ticketAPI = {
    getAll: async () => {
        const response = await api.get('/tickets/');
        return response.data;
    },

    getMy: async () => {
        const response = await api.get('/tickets/?my=1');
        return response.data;
    },

    create: async (formData) => {
        const response = await api.post('/tickets/', formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
        });
        return response.data;
    },

    getDetail: async (id) => {
        const response = await api.get(`/tickets/${id}/`);
        return response.data;
    },

    updateStatus: async (id, stav) => {
        const response = await api.patch(`/tickets/${id}/`, { stav });
        return response.data;
    },

    addComment: async (id, text) => {
        const response = await api.post(`/tickets/${id}/comments/`, { text });
        return response.data;
    },

    updateComment: async (ticketId, commentId, text) => {
        const response = await api.patch(`/tickets/${ticketId}/comments/${commentId}/`, { text });
        return response.data;
    },

    deleteComment: async (ticketId, commentId) => {
        const response = await api.delete(`/tickets/${ticketId}/comments/${commentId}/`);
        return response.data;
    },

    deleteTicket: async (id) => {
        const response = await api.delete(`/tickets/${id}/`);
        return response.data;
    },

    getUnreadSummary: async () => {
        const response = await api.get('/tickets/unread-summary/');
        return response.data;
    },

    markRead: async (id) => {
        const response = await api.post(`/tickets/${id}/mark-read/`);
        return response.data;
    },

    markAllRead: async () => {
        const response = await api.post('/tickets/mark-all-read/');
        return response.data;
    },
};

export const shiftsAttendanceAPI = {
    getTodayWorkBoard: async () => {
        const response = await api.get('/shifts/attendance/today-board/');
        return response.data;
    },
};

export const taskAPI = {
    getDashboardSnapshot: async () => {
        const response = await api.get('/tasks/dashboard-snapshot/');
        return response.data;
    },
    getUnreadSummary: async () => {
        const response = await api.get('/tasks/unread-summary/');
        return response.data;
    },
    getNotificationsSummary: async () => {
        const response = await api.get('/tasks/notifications-summary/');
        return response.data;
    },
    list: async (params = {}) => {
        const query = typeof params === 'string' ? { stav: params } : params;
        const response = await api.get('/tasks/', { params: query });
        return response.data;
    },
    get: async (taskId) => {
        const response = await api.get(`/tasks/${taskId}/`);
        return response.data;
    },
    getCalendar: async (mesic, extra = {}) => {
        const response = await api.get('/tasks/calendar/', { params: { mesic, ...extra } });
        return response.data;
    },
    getAssignees: async (prodejnaId, { storeless = false } = {}) => {
        const params = storeless ? { storeless: '1' } : { prodejna_id: prodejnaId };
        const response = await api.get('/tasks/assignees/', { params });
        return response.data;
    },
    listComments: async (taskId) => {
        const response = await api.get(`/tasks/${taskId}/comments/`);
        return response.data;
    },
    addComment: async (taskId, text) => {
        const response = await api.post(`/tasks/${taskId}/comments/`, { text });
        return response.data;
    },
    markRead: async (id) => {
        const response = await api.post(`/tasks/${id}/mark-read/`);
        return response.data;
    },
    create: async (payload) => {
        const response = await api.post('/tasks/', payload);
        return response.data;
    },
    update: async (id, payload) => {
        const response = await api.put(`/tasks/${id}/`, payload);
        return response.data;
    },
    delete: async (id) => {
        const response = await api.delete(`/tasks/${id}/`);
        return response.data;
    },
};

export const profileAPI = {
    getProfile: async () => {
        const response = await api.get('/users/profile/');
        return response.data;
    },
};

export const newsAPI = {
    list: async (params = {}) => {
        const response = await api.get('/news/', { params });
        return response.data;
    },
};

export const shiftsAPI = {
    listByMonth: async (mesic) => {
        const response = await api.get('/shifts/', { params: { mesic } });
        return response.data;
    },
    /** Úzký výřez pro dashboard (např. jen dnešek / od data + limit). */
    list: async (params = {}) => {
        const response = await api.get('/shifts/', { params });
        return response.data;
    },
    getTodayWorkBoard: async () => {
        const response = await api.get('/shifts/attendance/today-board/');
        return response.data;
    },
};

export const leaderboardAPI = {
    /** @param {string} url – plná cesta z getApiEndpoints() */
    fetch: async (url, params = {}) => {
        const path = url.startsWith('/api') ? url.slice(4) : url;
        const response = await api.get(path, { params });
        return response.data;
    },
};

export const plansAPI = {
    getAuditZbytek: async (rok, mesic) => (await api.get(`/plans/${rok}/${mesic}/audit-zbytek/`)).data,
    getAuditZbytekPolozky: async (rok, mesic, { kategorie, kategorie_1 = '', limit = 500, offset = 0 } = {}) => {
        const params = new URLSearchParams({
            kategorie,
            kategorie_1: kategorie_1 || '',
            limit: String(limit),
            offset: String(offset),
        });
        return (await api.get(`/plans/${rok}/${mesic}/audit-zbytek/polozky/?${params}`)).data;
    },
    getPlneni: async (rok, mesic) => (await api.get(`/plans/${rok}/${mesic}/plneni/`)).data,
    getPlneniProdejci: async (rok, mesic) => (await api.get(`/plans/${rok}/${mesic}/plneni-prodejci/`)).data,
    getPlneniPolozky: async (rok, mesic, params) => (
        await api.get(`/plans/${rok}/${mesic}/plneni-polozky/`, { params })
    ).data,
    getHistorie3mNahled: async (rok, mesic, rustProcent = 10) => (
        await api.get(`/plans/${rok}/${mesic}/historie-3m-nahled/`, { params: { rust_procent: rustProcent } })
    ).data,
    getHistorieNahled: async (rok, mesic, rustProcent = 10) => (
        await api.get(`/plans/${rok}/${mesic}/historie-nahled/`, { params: { rust_procent: rustProcent } })
    ).data,
    getHistorieAutoNahled: async (rok, mesic, rustProcent = 10) => (
        await api.get(`/plans/${rok}/${mesic}/historie-auto-nahled/`, { params: { rust_procent: rustProcent } })
    ).data,
    getForecast: async (rok, rustProcent = 10, rokyPorovnani = [], prodejnaIds = null) => {
        const ids = Array.isArray(prodejnaIds) ? prodejnaIds.filter(Boolean) : (prodejnaIds ? [prodejnaIds] : []);
        return (await api.get('/plans/forecast/', {
            params: {
                rok,
                rust: rustProcent,
                roky: rokyPorovnani.length ? rokyPorovnani.join(',') : undefined,
                prodejna_ids: ids.length ? ids.join(',') : undefined,
                prodejna_id: ids.length === 1 ? ids[0] : undefined,
            },
        })).data;
    },
    createForecastYear: async (rok, rustProcent = 10, skipExisting = true) => (
        await api.post('/plans/forecast/create-year/', {
            rok,
            rust_procent: rustProcent,
            skip_existing: skipExisting,
        })
    ).data,
    getPlan: async (rok, mesic) => (await api.get(`/plans/${rok}/${mesic}/`)).data,
    getVerze: async (verzeId) => (await api.get(`/plans/verze/${verzeId}/`)).data,
    createPlan: async (rok, mesic, payload) => (await api.post(`/plans/${rok}/${mesic}/`, payload)).data,
    prodejciAuto: async (planProdejnaId) => (
        await api.post(`/plans/prodejna/${planProdejnaId}/prodejci/auto/`)
    ).data,
    prepocet: async (rok, mesic, payload) => (await api.post(`/plans/${rok}/${mesic}/prepocet/`, payload)).data,
    ulozit: async (rok, mesic, payload) => (await api.put(`/plans/${rok}/${mesic}/ulozit/`, payload)).data,
    setAktualniVerze: async (verzeId) => (await api.post(`/plans/verze/${verzeId}/set-aktualni/`)).data,
    getProdejci: async (planProdejnaId) => (await api.get(`/plans/prodejna/${planProdejnaId}/prodejci/`)).data,
    ulozitProdejci: async (planProdejnaId, payload) => (
        await api.post(`/plans/prodejna/${planProdejnaId}/prodejci/ulozit/`, payload)
    ).data,
    getMujPlan: async (rok, mesic) => (
        await api.get('/plans/muj-plan/', { params: { rok, mesic } })
    ).data,
};

export default api;

export const analyticsAPI = {
    getActorStatus: async () => {
        const response = await api.get('/analytics/backup-info/');
        return response.data;
    },
    get: async (path, params = {}) => {
        const clean = path
            .replace(/^\/api\/analytics\//, '')
            .replace(/^\/analytics\//, '')
            .replace(/^\//, '');
        const queryParams = params instanceof URLSearchParams
            ? Object.fromEntries(params.entries())
            : params;
        const response = await api.get(`/analytics/${clean}`, { params: queryParams });
        return response.data;
    },
};

export const packetaAPI = {
    getStatus: async () => (await api.get('/packeta/status/')).data,
    importCsv: async (file, prodejnaId) => {
        const form = new FormData();
        form.append('file', file);
        form.append('prodejna_id', String(prodejnaId));
        const response = await api.post('/packeta/import-csv/', form, {
            headers: { 'Content-Type': 'multipart/form-data' },
        });
        return response.data;
    },
    fetchAll: async (days = 1) => (
        await api.post('/packeta/fetch/', { days })
    ).data,
};

export const financeAPI = {
    getStatus: async () => (await api.get('/finance/status/')).data,
    getKategorie: async () => (await api.get('/finance/kategorie/')).data,
    getNezarazene: async (params = {}) => (
        await api.get('/finance/naklady/nezarazene/', { params })
    ).data,
    getPrehled: async (params = {}) => (
        await api.get('/finance/naklady/prehled/', { params })
    ).data,
    getCekaNaFakturu: async () => (await api.get('/finance/naklady/ceka-na-fakturu/')).data,
    getDokladyKeKontrole: async () => (await api.get('/finance/doklady/ke-kontrole/')).data,
    createManualNaklad: async (payload) => (
        await api.post('/finance/naklady/manual/', payload)
    ).data,
    updateNaklad: async (id, payload) => (
        await api.patch(`/finance/naklady/${id}/`, payload)
    ).data,
    getPravidla: async () => (await api.get('/finance/pravidla/')).data,
    createPravidlo: async (payload) => (await api.post('/finance/pravidla/', payload)).data,
    deletePravidlo: async (id) => (await api.delete(`/finance/pravidla/${id}/`)).data,
    uploadDoklad: async ({
        file,
        naklad_polozka_id,
        cislo_faktury,
        dodavatel_nazev,
        castka_bez_dph,
        dph_castka,
        dph_sazba,
    }) => {
        const form = new FormData();
        form.append('file', file);
        form.append('naklad_polozka_id', String(naklad_polozka_id));
        if (cislo_faktury) form.append('cislo_faktury', cislo_faktury);
        if (dodavatel_nazev) form.append('dodavatel_nazev', dodavatel_nazev);
        if (castka_bez_dph) form.append('castka_bez_dph', castka_bez_dph);
        if (dph_castka) form.append('dph_castka', dph_castka);
        if (dph_sazba) form.append('dph_sazba', dph_sazba);
        const response = await api.post('/finance/doklady/upload/', form, {
            headers: { 'Content-Type': 'multipart/form-data' },
        });
        return response.data;
    },
    schvalitDoklad: async (id) => (await api.post(`/finance/doklady/${id}/schvalit/`)).data,
    zamitnoutDoklad: async (id, payload = {}) => (
        await api.post(`/finance/doklady/${id}/zamitnout/`, payload)
    ).data,
    reprocessDokladOcr: async (id) => (
        await api.post(`/finance/doklady/${id}/reprocess-ocr/`)
    ).data,
};

export const reklamaceAPI = {
    listNotifications: async ({ unread = true } = {}) => {
        const params = unread ? {} : { read: '1' };
        const response = await api.get('/reklamace/notifikace/', { params });
        return response.data;
    },
    listUnreadNotifications: async () => reklamaceAPI.listNotifications({ unread: true }),
    markNotificationsRead: async (ids) => {
        const response = await api.post('/reklamace/notifikace/mark-read/', { ids });
        return response.data;
    },
};

export const coachingAPI = {
    getFilters: async () => (await api.get('/coaching/filters/options/')).data,
    getRoster: async (params = {}) => (await api.get('/coaching/roster/', { params })).data,
    getSellerProfile: async (userId, params = {}) => (
        await api.get(`/coaching/sellers/${userId}/profile/`, { params })
    ).data,
    getSellerTimeline: async (userId, params = {}) => (
        await api.get(`/coaching/sellers/${userId}/timeline/`, { params })
    ).data,
    getSellerTasks: async (userId, params = {}) => (
        await api.get(`/coaching/sellers/${userId}/tasks/`, { params })
    ).data,
    compareSellers: async (params = {}) => (await api.get('/coaching/sellers/compare/', { params })).data,
    listNotes: async (params = {}) => (await api.get('/coaching/notes/', { params })).data,
    createNote: async (payload) => (await api.post('/coaching/notes/', payload)).data,
    updateNote: async (id, payload) => (await api.patch(`/coaching/notes/${id}/`, payload)).data,
    deleteNote: async (id) => (await api.delete(`/coaching/notes/${id}/`)).data,
    listGoals: async (params = {}) => (await api.get('/coaching/goals/', { params })).data,
    createGoal: async (payload) => (await api.post('/coaching/goals/', payload)).data,
    updateGoal: async (id, payload) => (await api.patch(`/coaching/goals/${id}/`, payload)).data,
    deleteGoal: async (id) => (await api.delete(`/coaching/goals/${id}/`)).data,
};