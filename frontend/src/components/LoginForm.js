import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { peekReturnPath } from '../utils/authReturnPath';
import './LoginForm.css';

const LoginForm = () => {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const { login, loading, error } = useAuth();
    const returnPath = peekReturnPath();
    const deepLinkHint = returnPath && returnPath.includes('id=');

    const handleSubmit = async (e) => {
        e.preventDefault();

        if (!username || !password) {
            return;
        }

        await login(username, password);
    };

    return (
        <div className="login-container">
            <div className="login-card">
                <header className="login-card__header">
                    <h1 className="login-card__title">Přihlášení</h1>
                    <p className="login-card__subtitle">
                        {deepLinkHint
                            ? 'Po přihlášení vás přesměrujeme přímo na úkol z odkazu.'
                            : 'Zadejte své přihlašovací údaje pro přístup k datům a statistikám.'}
                    </p>
                </header>

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
                        <span className="arrow-icon" aria-hidden="true">→</span>
                    </button>
                </form>
            </div>
        </div>
    );
};

export default LoginForm;
