import React, { useState, useEffect } from 'react';
import './AccessForm.css';

const AccessForm = ({ access, stores, categories, onSubmit, onCancel }) => {
    const [formData, setFormData] = useState({
        company_name: '',
        website_url: '',
        username: '',
        password: '',
        category: '',
        store: '',
        description: '',
        notes: ''
    });
    const [errors, setErrors] = useState({});
    const [loading, setLoading] = useState(false);

    // Získání unikátních názvů prodejen ze statistik
    const storeNames = stores.map(store => store.store);

    useEffect(() => {
        if (access) {
            setFormData({
                company_name: access.company_name || '',
                website_url: access.website_url || '',
                username: access.username || '',
                password: access.password || '',
                category: access.category || '',
                store: access.store || '',
                description: access.description || '',
                notes: access.notes || ''
            });
        }
    }, [access]);

    const handleChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({
            ...prev,
            [name]: value
        }));
        
        // Vymazání chyby pro dané pole
        if (errors[name]) {
            setErrors(prev => ({
                ...prev,
                [name]: ''
            }));
        }
    };

    const validateForm = () => {
        const newErrors = {};

        if (!formData.company_name.trim()) {
            newErrors.company_name = 'Název společnosti je povinný';
        }

        if (!formData.store.trim()) {
            newErrors.store = 'Prodejna je povinná';
        }

        if (!formData.username.trim()) {
            newErrors.username = 'Uživatelské jméno je povinné';
        }

        if (!formData.password.trim()) {
            newErrors.password = 'Heslo je povinné';
        }

        if (formData.website_url && !isValidUrl(formData.website_url)) {
            newErrors.website_url = 'Neplatná URL adresa';
        }

        setErrors(newErrors);
        return Object.keys(newErrors).length === 0;
    };

    const isValidUrl = (string) => {
        try {
            new URL(string.startsWith('http') ? string : 'https://' + string);
            return true;
        } catch (_) {
            return false;
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        
        if (!validateForm()) {
            return;
        }

        setLoading(true);
        try {
            await onSubmit(formData);
        } catch (error) {
            console.error('Error submitting form:', error);
        } finally {
            setLoading(false);
        }
    };

    const generatePassword = () => {
        const length = 12;
        const charset = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*";
        let password = "";
        for (let i = 0; i < length; i++) {
            password += charset.charAt(Math.floor(Math.random() * charset.length));
        }
        setFormData(prev => ({ ...prev, password }));
    };

    return (
        <div className="access-form-overlay">
            <div className="access-form-modal">
                <div className="form-header">
                    <h3>
                        {access ? '✏️ Upravit přístup' : '➕ Přidat nový přístup'}
                    </h3>
                    <button 
                        className="btn-close"
                        onClick={onCancel}
                        type="button"
                    >
                        ✕
                    </button>
                </div>

                <form onSubmit={handleSubmit} className="access-form">
                    <div className="form-grid">
                        <div className="form-group">
                            <label htmlFor="company_name">
                                Název společnosti *
                            </label>
                            <input
                                type="text"
                                id="company_name"
                                name="company_name"
                                value={formData.company_name}
                                onChange={handleChange}
                                className={errors.company_name ? 'error' : ''}
                                placeholder="např. Google, Facebook, Apple..."
                            />
                            {errors.company_name && (
                                <span className="error-text">{errors.company_name}</span>
                            )}
                        </div>

                        <div className="form-group">
                            <label htmlFor="store">
                                Prodejna *
                            </label>
                            <select
                                id="store"
                                name="store"
                                value={formData.store}
                                onChange={handleChange}
                                className={errors.store ? 'error' : ''}
                            >
                                <option value="">Vyberte prodejnu</option>
                                {storeNames.map(storeName => (
                                    <option key={storeName} value={storeName}>
                                        {storeName}
                                    </option>
                                ))}
                            </select>
                            {errors.store && (
                                <span className="error-text">{errors.store}</span>
                            )}
                        </div>

                        <div className="form-group">
                            <label htmlFor="website_url">
                                URL adresa
                            </label>
                            <input
                                type="url"
                                id="website_url"
                                name="website_url"
                                value={formData.website_url}
                                onChange={handleChange}
                                className={errors.website_url ? 'error' : ''}
                                placeholder="https://example.com"
                            />
                            {errors.website_url && (
                                <span className="error-text">{errors.website_url}</span>
                            )}
                        </div>

                        <div className="form-group">
                            <label htmlFor="category">
                                Kategorie
                            </label>
                            <select
                                id="category"
                                name="category"
                                value={formData.category}
                                onChange={handleChange}
                            >
                                <option value="">Vyberte kategorii</option>
                                {categories.map(category => (
                                    <option key={category} value={category}>
                                        {category}
                                    </option>
                                ))}
                                <option value="Dodavatel">Dodavatel</option>
                                <option value="E-shop">E-shop</option>
                                <option value="Admin">Admin</option>
                                <option value="Marketing">Marketing</option>
                                <option value="Ostatní">Ostatní</option>
                            </select>
                        </div>

                        <div className="form-group">
                            <label htmlFor="username">
                                Uživatelské jméno *
                            </label>
                            <input
                                type="text"
                                id="username"
                                name="username"
                                value={formData.username}
                                onChange={handleChange}
                                className={errors.username ? 'error' : ''}
                                placeholder="uživatelské jméno nebo email"
                            />
                            {errors.username && (
                                <span className="error-text">{errors.username}</span>
                            )}
                        </div>

                        <div className="form-group">
                            <label htmlFor="password">
                                Heslo *
                            </label>
                            <div className="password-input-group">
                                <input
                                    type="password"
                                    id="password"
                                    name="password"
                                    value={formData.password}
                                    onChange={handleChange}
                                    className={errors.password ? 'error' : ''}
                                    placeholder="heslo"
                                />
                                <button
                                    type="button"
                                    className="btn-generate"
                                    onClick={generatePassword}
                                    title="Generovat náhodné heslo"
                                >
                                    🎲
                                </button>
                            </div>
                            {errors.password && (
                                <span className="error-text">{errors.password}</span>
                            )}
                        </div>
                    </div>

                    <div className="form-group full-width">
                        <label htmlFor="description">
                            Popis
                        </label>
                        <textarea
                            id="description"
                            name="description"
                            value={formData.description}
                            onChange={handleChange}
                            rows="3"
                            placeholder="Stručný popis účelu tohoto přístupu..."
                        />
                    </div>

                    <div className="form-group full-width">
                        <label htmlFor="notes">
                            Poznámky
                        </label>
                        <textarea
                            id="notes"
                            name="notes"
                            value={formData.notes}
                            onChange={handleChange}
                            rows="3"
                            placeholder="Dodatečné poznámky, instrukce nebo důležité informace..."
                        />
                    </div>

                    <div className="form-actions">
                        <button
                            type="button"
                            className="btn-secondary"
                            onClick={onCancel}
                            disabled={loading}
                        >
                            Zrušit
                        </button>
                        <button
                            type="submit"
                            className="btn-primary"
                            disabled={loading}
                        >
                            {loading ? (
                                <>
                                    <span className="spinner-small"></span>
                                    Ukládám...
                                </>
                            ) : (
                                access ? 'Uložit změny' : 'Přidat přístup'
                            )}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

export default AccessForm; 