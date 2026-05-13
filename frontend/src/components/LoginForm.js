import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import './LoginForm.css';

const LoginForm = () => {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const { login, loading, error } = useAuth();

    const handleSubmit = async (e) => {
        e.preventDefault();
        
        if (!username || !password) {
            return;
        }

        await login(username, password);
    };

    return (
        <div className="login-container">
            <div className="login-header">
                <h1>Přihlášení do systému</h1>
                <p>Zadejte své přihlašovací údaje pro přístup k datům a statistikám.</p>
            </div>
            
            <div className="login-card">
                <div className="login-card-header">
                    <span className="lock-icon">🔒</span>
                    <h2>Přihlášení</h2>
                </div>
                
                <form onSubmit={handleSubmit} className="login-form">
                    <div className="form-group">
                        <label htmlFor="username">Uživatelské jméno</label>
                        <input
                            type="text"
                            id="username"
                            value={username}
                            onChange={(e) => setUsername(e.target.value)}
                            placeholder="Zadejte uživatelské jméno"
                            required
                        />
                    </div>
                    
                    <div className="form-group">
                        <label htmlFor="password">Heslo</label>
                        <input
                            type="password"
                            id="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            placeholder="Zadejte heslo"
                            required
                        />
                    </div>
                    
                    {error && (
                        <div className="error-message">
                            {error}
                        </div>
                    )}
                    
                    <button 
                        type="submit" 
                        className="login-button"
                        disabled={loading}
                    >
                        {loading ? 'Přihlašování...' : 'Přihlásit se'}
                        <span className="arrow-icon">→</span>
                    </button>
                </form>
            </div>
        </div>
    );
};

export default LoginForm; 