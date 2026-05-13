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
            console.log('Kontroluji autentifikaci...');
            const response = await userAPI.getCurrentUser();
            console.log('Odpověď z API:', response);
            if (response.success) {
                setUser(response.user);
                console.log('Uživatel načten:', response.user);
            } else {
                console.log('Uživatel není přihlášen:', response.message);
                setUser(null);
            }
        } catch (error) {
            console.log('Uživatel není přihlášen - chyba:', error.message);
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

    const hasModuleAccess = (moduleName) => {
        if (!user) return false;
        return user.moduly && user.moduly.includes(moduleName);
    };

    const isAdmin = () => {
        return user && user.role === 'ADMIN';
    };

    const value = {
        user,
        loading,
        error,
        login,
        logout,
        hasModuleAccess,
        isAdmin,
    };

    return (
        <AuthContext.Provider value={value}>
            {children}
        </AuthContext.Provider>
    );
}; 