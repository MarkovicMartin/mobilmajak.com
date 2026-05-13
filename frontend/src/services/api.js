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
        console.log('CSRF token přidán:', csrfToken);
    } else {
        console.log('CSRF token nenalezen v cookies');
    }
    
    return config;
});



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

    // Seznam uživatelů (ADMIN + VEDOUCI)
    getUsers: async () => {
        const response = await api.get('/users/list/');
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
};

export default api; 

// API funkce pro analytiku
export const analyticsAPI = {
    // Stav Apify/actor importu (poslední běh, počty záznamů)
    getActorStatus: async () => {
        // Preferujeme nové WEB_PRODEJE info; apify slouží jako fallback
        try {
            const response = await api.get('/analytics/backup-info/');
            return response.data;
        } catch (_e) {
            const response = await api.get('/analytics/apify/backup-info/');
            return response.data;
        }
    },
};

// API pro chatbota (admin-only)
// (chatbot odstraněn)