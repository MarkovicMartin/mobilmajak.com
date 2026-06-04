import React, { createContext, useContext, useState, useEffect } from 'react';
import { userAPI } from '../services/api';

const AuthContext = createContext();

export const useAuth = () => {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
};

export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    // Kontrola, zda je uživatel přihlášen při načtení aplikace
    useEffect(() => {
        checkAuthStatus();
    }, []);

    const checkAuthStatus = async () => {
        try {
            const response = await userAPI.getCurrentUser();
            if (response.success) {
                setUser(response.user);
            } else {
                setUser(null);
            }
        } catch {
            setUser(null);
        } finally {
            setLoading(false);
        }
    };

    const login = async (username, password) => {
        setLoading(true);
        setError(null);
        
        try {
            const response = await userAPI.login(username, password);
            if (response.success) {
                setUser(response.user);
                return { success: true };
            } else {
                setError(response.message || 'Přihlášení selhalo');
                return { success: false, error: response.message };
            }
        } catch (error) {
            const errorMessage = error.response?.data?.message || 'Chyba při přihlašování';
            setError(errorMessage);
            return { success: false, error: errorMessage };
        } finally {
            setLoading(false);
        }
    };

    const logout = async () => {
        try {
            await userAPI.logout();
        } catch (error) {
            console.error('Chyba při odhlašování:', error);
        } finally {
            setUser(null);
            setError(null);
        }
    };

    const isAdmin = () => user?.role === 'ADMIN';

    const canManageTasks = () => {
        if (!user) return false;
        if (user.can_manage_tasks === true) return true;
        return user.role === 'ADMIN' || user.role === 'VEDOUCI' || !!user.vedouci_prodejna_id;
    };

    const canAccessCoaching = canManageTasks;

    const canManageTickets = () => {
        if (!user) return false;
        if (user.role === 'ADMIN') return true;
        if (user.can_manage_tickets === true) return true;
        return Array.isArray(user.moduly) && user.moduly.includes('tickets_admin');
    };

    const value = {
        user,
        loading,
        error,
        login,
        logout,
        isAdmin,
        canManageTasks,
        canAccessCoaching,
        canManageTickets,
    };

    return (
        <AuthContext.Provider value={value}>
            {children}
        </AuthContext.Provider>
    );
}; 